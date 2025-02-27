from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import types
from queue import Queue
from typing import Any, Dict, Iterable, List, Set, Type

from BlockServer.core.config_list_manager import ConfigListManager
from BlockServer.core.macros import PVPREFIX_MACRO
from server_common.channel_access import ChannelAccess
from server_common.helpers import MACROS
from server_common.utilities import SEVERITY
from server_common.utilities import print_and_log as _common_print_and_log


def print_and_log(message: str, *args, **kwargs) -> None:
    _common_print_and_log(f"ComponentSwitcher: {message}", *args, **kwargs)


class ComponentSwitcherConfigFileManager(object):
    CONF_FILE_PATH = os.path.join(
        MACROS["$(ICPCONFIGROOT)"], "ComponentSwitcher", "component_switcher.json"
    )

    def read_config(self) -> List[Dict[str, Any]]:
        """
        Reads a config file from JSON on disk and returns it as a python object
        """
        if os.path.exists(self.CONF_FILE_PATH):
            with open(self.CONF_FILE_PATH) as f:
                return json.loads(f.read())
        else:
            print_and_log(
                f"component_switcher config file at {self.CONF_FILE_PATH} does not exist"
                f" - assuming empty config",
                SEVERITY.MINOR,
            )
            return []


class ComponentSwitcher(object):
    def __init__(
        self,
        config_list: ConfigListManager,
        blockserver_write_queue: Queue,
        reload_current_config_func: types.FunctionType,
        file_manager: ComponentSwitcherConfigFileManager = None,
        channel_access_class: Type[ChannelAccess] = None,
    ) -> None:
        self._config_list = config_list
        self._blockserver_write_queue = blockserver_write_queue
        self._reload_current_config = reload_current_config_func

        self._ca_class = channel_access_class if channel_access_class is not None else ChannelAccess
        self._file_manager = (
            file_manager if file_manager is not None else ComponentSwitcherConfigFileManager()
        )

    def all_components_dynamic(self, components: Iterable[str]) -> bool:
        for comp in components:
            try:
                loaded_comp = self._config_list.load_config(comp, is_component=True)
                if not loaded_comp.is_dynamic():
                    print_and_log(f"Component is not dynamic: {comp}")
                    return False
            except Exception as e:
                print_and_log(f"Error while checking whether component {comp} is dynamic: {e}")
                return False
        return True

    def create_monitors(self) -> None:
        """
        Starts monitoring the PVs specified in the configswitcher configuration file.
        """
        for item in self._file_manager.read_config():
            pv = item["pv"]
            pv_is_local = item["is_local"]
            value_to_component_map = item["value_to_component_map"]

            if pv_is_local:
                pv = MACROS[PVPREFIX_MACRO] + pv

            if not self.all_components_dynamic(value_to_component_map.values()):
                print_and_log(
                    f"ERROR: not adding monitor to PV {pv} as some of the requested "
                    f"components are not marked as dynamic."
                )
                continue

            print_and_log("Adding monitor to PV {}".format(pv))

            def callback(val: Any, stat: int, sevr: int) -> None:
                """
                Callback function called when the monitored PV changes.

                Args:
                    val: the value that this monitor returned
                    stat: the epics status of the monitored PV
                    sevr: the epics severity of the monitored PV
                """
                val = str(val)

                if stat != 0 or sevr != 0:
                    print_and_log(
                        f"Got value '{val}' (stat={stat}, sevr={sevr}) for pv '{pv}', ignoring as it has "
                        f"non-zero STAT/SEVR"
                    )
                    return

                if val not in value_to_component_map:
                    print_and_log(
                        f"Got value '{val}' (stat={stat}, sevr={sevr}) for pv '{pv}', ignoring as value did "
                        f"not map to any component"
                    )
                    return

                comps_to_remove = {v for k, v in value_to_component_map.items() if k != val}
                comps_to_add = {value_to_component_map[val]}

                print_and_log(
                    f"Got value '{val}' (stat={stat}, sevr={sevr}) for pv '{pv}'. Editing configurations to "
                    f"remove components {comps_to_remove} and add components {comps_to_add}."
                )

                # Put these actions onto the blockserver write queue so that we avoid any multithreading problems
                # with concurrent edits from multiple sources in the blockserver. This also ensures we don't do any
                # CA calls from within a monitor context, which would be invalid.
                self._blockserver_write_queue.put(
                    (
                        self._edit_all_configurations,
                        (comps_to_remove, comps_to_add),
                        "COMPONENT_SWITCHER_EDIT",
                    )
                )

            self._ca_class.add_monitor(pv, callback)

    def _edit_all_configurations(
        self, components_to_be_removed: Set[str], components_to_be_added: Set[str]
    ) -> None:
        """
        Edits all configurations by adding or removing the specified components.

        Args:
            components_to_be_removed: A set of component names which will be removed from all configurations if present
            components_to_be_added: A set of component names which will be added to all configurations
        """

        current_config_name = self._config_list.active_config_name

        config_names = {meta["name"] for meta in self._config_list.get_configs()}
        component_names = {meta["name"] for meta in self._config_list.get_components()}

        if current_config_name not in config_names:
            raise ValueError(
                f"current config {current_config_name} not in list of all configs {config_names}."
            )

        if not components_to_be_removed.issubset(component_names):
            raise ValueError(
                f"A component for removal did not exist. "
                f"Remove {components_to_be_removed}, available {component_names}"
            )

        if not components_to_be_added.issubset(component_names):
            raise ValueError(
                f"A component to be added did not exist. "
                f"Add {components_to_be_added}, available {component_names}"
            )

        for config_name in config_names:
            config_changed = False
            config = self._config_list.load_config(config_name, is_component=False)

            # Remove components first to avoid any conflicts
            for component_name in components_to_be_removed:
                if component_name in config.get_component_names():
                    print_and_log(f"Removing component {component_name} from {config_name}")
                    config.remove_comp(component_name)
                    config_changed = True

            for component_name in components_to_be_added:
                if component_name not in config.get_component_names():
                    print_and_log(f"Adding component {component_name} to {config_name}")
                    config.add_component(component_name)
                    config_changed = True

            if config_changed:
                print_and_log(f"Saving modified config {config_name}")
                config.save_inactive()
                self._config_list.update(config)

                if config_name == current_config_name:
                    print_and_log(f"Reloading active modified config ({config_name})")
                    self._reload_current_config()
