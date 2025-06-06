# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2016 Science & Technology Facilities Council.
# All rights reserved.
#
# This program is distributed in the hope that it will be useful.
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v1.0 which accompanies this distribution.
# EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM
# AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
# You should have received a copy of the Eclipse Public License v1.0
# along with this program; if not, you can obtain a copy from
# https://www.eclipse.org/org/documents/epl-v10.php or
# http://opensource.org/licenses/eclipse-1.0.php

# Add root path for access to server_commons and path for version control module
import contextlib
import json
import os
import sys
import traceback
from typing import Any, Dict

from server_common.channel_access import ManagerModeRequiredError, verify_manager_mode
from server_common.channel_access_server import CAServer

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Standard imports
import argparse
import datetime
from importlib.resources import as_file, files
from queue import Queue
from threading import RLock, Thread
from time import sleep, time

from pcaspy import Driver, SimpleServer
from pcaspy.driver import Data, manager
from server_common.channel_access import ChannelAccess
from server_common.file_path_manager import FILEPATH_MANAGER
from server_common.helpers import BLOCK_PREFIX, CONTROL_SYSTEM_PREFIX, MACROS, PVPREFIX_MACRO
from server_common.pv_names import BlockserverPVNames
from server_common.utilities import (
    char_waveform,
    compress_and_hex,
    convert_from_json,
    convert_to_json,
    dehex_and_decompress,
    print_and_log,
    set_logger,
)

from BlockServer.component_switcher.component_switcher import ComponentSwitcher
from BlockServer.config.json_converter import ConfigurationJsonConverter
from BlockServer.core.active_config_holder import ActiveConfigHolder
from BlockServer.core.config_list_manager import ConfigListManager
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.ioc_control import IocControl
from BlockServer.devices.devices_manager import DevicesManager
from BlockServer.epics.archiver_manager import ArchiverManager
from BlockServer.epics.gateway import Gateway
from BlockServer.fileIO.file_manager import ConfigurationFileManager
from BlockServer.mocks.mock_version_control import MockVersionControl
from BlockServer.runcontrol.runcontrol_manager import RunControlManager
from BlockServer.site_specific.default.block_rules import BlockRules
from BlockServer.site_specific.default.general_rules import (
    ConfigurationDescriptionRules,
    GroupRules,
)
from BlockServer.synoptic.synoptic_manager import SynopticManager
from ConfigVersionControl.git_version_control import GitVersionControl, RepoFactory
from ConfigVersionControl.version_control_exceptions import (
    NotUnderVersionControl,
    VersionControlException,
)
from WebServer.simple_webserver import Server

CURR_CONFIG_NAME_SEVR_VALUE = 0
CONFIG_PUSH_TIME = 300  # 5 minutes
INST_SCRIPT_PUSH_TIME = 604800  # 7 days

# This IOC gets special treatment as it needs to be reloaded on every single config change,
# regardless of whether it's macros have changed or not.
# For details see https://github.com/ISISComputingGroup/IBEX/issues/5590
CAEN_DISCRIMINATOR_IOC_NAME = "CAENV895_01"

# For documentation on these commands see the wiki
initial_dbs = {
    BlockserverPVNames.BLOCKNAMES: char_waveform(16000),
    BlockserverPVNames.HEARTBEAT: {"type": "int", "count": 1, "value": [0]},
    BlockserverPVNames.WD_CONF_DETAILS: char_waveform(16000),
    BlockserverPVNames.GROUPS: char_waveform(16000),
    BlockserverPVNames.COMPS: char_waveform(16000),
    BlockserverPVNames.LOAD_CONFIG: char_waveform(1000),
    BlockserverPVNames.RELOAD_CURRENT_CONFIG: char_waveform(100),
    BlockserverPVNames.START_IOCS: char_waveform(16000),
    BlockserverPVNames.STOP_IOCS: char_waveform(1000),
    BlockserverPVNames.RESTART_IOCS: char_waveform(1000),
    BlockserverPVNames.CONFIGS: char_waveform(16000),
    BlockserverPVNames.GET_CURR_CONFIG_DETAILS: char_waveform(64000),
    BlockserverPVNames.SET_CURR_CONFIG_DETAILS: char_waveform(64000),
    BlockserverPVNames.SAVE_NEW_CONFIG: char_waveform(64000),
    BlockserverPVNames.SAVE_NEW_COMPONENT: char_waveform(64000),
    BlockserverPVNames.SERVER_STATUS: char_waveform(1000),
    BlockserverPVNames.DELETE_CONFIGS: char_waveform(64000),
    BlockserverPVNames.DELETE_COMPONENTS: char_waveform(64000),
    BlockserverPVNames.BLANK_CONFIG: char_waveform(64000),
    BlockserverPVNames.ALL_COMPONENT_DETAILS: char_waveform(64000),
    BlockserverPVNames.BANNER_DESCRIPTION: char_waveform(16000),
    BlockserverPVNames.CURR_CONFIG_NAME: char_waveform(500),
    BlockserverPVNames.CURR_CONFIG_NAME_SEVR: {
        "type": "enum",
        "count": 1,
        "value": CURR_CONFIG_NAME_SEVR_VALUE,
        "enums": ["NO_ALARM"],
    },
}


class BlockServer(Driver):
    """The class for handling all the static PV access and monitors etc."""

    def __init__(self, ca_server: CAServer) -> None:
        """Constructor.

        Args:
            ca_server (CAServer): The CA server used for generating PVs on the fly
        """
        super(BlockServer, self).__init__()

        # Threading stuff
        self.monitor_lock = RLock()
        self.write_queue = Queue()

        FILEPATH_MANAGER.initialise(CONFIG_DIR, SCRIPT_DIR, SCHEMA_DIR)
        drive = os.path.abspath(".").split(os.path.sep)[0] + os.path.sep
        self.instrument_scripts = os.path.join(drive, "Instrument", "scripts")

        self.instrument_prefix = MACROS["$(MYPVPREFIX)"]
        self._cas = ca_server
        self._gateway = Gateway(
            GATEWAY_PREFIX,
            self.instrument_prefix,
            PVLIST_FILE,
            self.instrument_prefix + BLOCK_PREFIX,
        )
        self._active_configserver = None
        self._run_control = None
        self._syn = None
        self._devices = None
        self.on_the_fly_handlers = list()
        self._ioc_control = IocControl(self.instrument_prefix)
        self.block_rules = BlockRules(self)
        self.group_rules = GroupRules(self)
        self.config_desc = ConfigurationDescriptionRules(self)
        self.spangle_banner = json.dumps(ConfigurationFileManager.get_banner_config())

        # Connect to version control
        try:
            self._config_vc = GitVersionControl(
                CONFIG_DIR, RepoFactory.get_repo(CONFIG_DIR), "config", CONFIG_PUSH_TIME
            )
            self._config_vc.setup()
            print_and_log("Config version control initialised correctly", "INFO")
        except NotUnderVersionControl as err:
            print_and_log("Configurations not under version control: %s" % err, "MINOR")
            self._config_vc = MockVersionControl()
        except VersionControlException as err:
            print_and_log("Unable to initialise config version control: %s" % err, "MINOR")
            self._config_vc = MockVersionControl()
        except Exception as err:
            print_and_log("Unable to initialise config version control: %s" % err, "MINOR")
            self._config_vc = MockVersionControl()

        try:
            self._script_vc = GitVersionControl(
                self.instrument_scripts,
                RepoFactory.get_repo(self.instrument_scripts),
                "instrument scripts",
                INST_SCRIPT_PUSH_TIME,
            )
            self._script_vc.setup()
            print_and_log("Scripting version control initialised correctly", "INFO")
        except NotUnderVersionControl as err:
            print_and_log("Scripts not under version control: %s" % err, "MINOR")
            self._script_vc = MockVersionControl()
        except VersionControlException as err:
            print_and_log("Unable to initialise script version control: %s" % err, "MINOR")
            self._script_vc = MockVersionControl()
        except Exception as err:
            print_and_log("Unable to initialise script version control: %s" % err, "MINOR")
            self._script_vc = MockVersionControl()

        # Import data about all configs
        try:
            self._config_list = ConfigListManager(self, ConfigurationFileManager())
        except Exception as err:
            print_and_log(
                "Error creating inactive config list. "
                "Configuration list changes will not be stored "
                + "in version control: %s "
                % str(err),
                "MINOR",
            )
            self._config_list = ConfigListManager(self, ConfigurationFileManager())

        # Start a background thread for handling write commands
        write_thread = Thread(target=self.consume_write_queue, args=())
        write_thread.daemon = True  # Daemonise thread
        write_thread.start()

        self.write_queue.put((self.initialise_configserver, (FACILITY,), "INITIALISING"))

        # Starts the Web Server
        self.server = Server()
        self.server.start()

        self._component_switcher = ComponentSwitcher(
            self._config_list, self.write_queue, self.reload_current_config
        )
        self._component_switcher.create_monitors()

    def initialise_configserver(self, facility: str) -> None:
        """Initialises the ActiveConfigHolder.

        Args:
            facility (string): The facility using the BlockServer
        """
        # This is in a separate method so it can be sent to the thread queue
        arch = ArchiverManager(ARCHIVE_UPLOADER, ARCHIVE_SETTINGS)

        self._active_configserver = ActiveConfigHolder(
            MACROS, arch, ConfigurationFileManager(), self._ioc_control, CONFIG_DIR
        )

        if facility == "ISIS":
            self._run_control = RunControlManager(
                self.instrument_prefix,
                MACROS["$(ICPCONFIGROOT)"],
                MACROS["$(ICPVARDIR)"],
                self._ioc_control,
                self._active_configserver,
                self,
            )
            self.on_the_fly_handlers.append(self._run_control)

        # Import all the synoptic data and create PVs
        print_and_log("Creating synoptic manager...")
        self._syn = SynopticManager(self, SCHEMA_DIR, self._active_configserver)
        self.on_the_fly_handlers.append(self._syn)
        print_and_log("Finished creating synoptic manager")

        # Import all the devices data and create PVs
        print_and_log("Creating devices manager...")
        self._devices = DevicesManager(self, SCHEMA_DIR)
        self.on_the_fly_handlers.append(self._devices)
        print_and_log("Finished creating devices manager")

        try:
            if self._gateway.exists():
                print_and_log("Found gateway")
                self.load_last_config()
            else:
                print_and_log("Could not connect to gateway - is it running?")
                self.load_last_config()
        except Exception as err:
            print_and_log("Could not load last configuration. Message was: %s" % err, "MAJOR")
            self._active_configserver.clear_config()
            self._initialise_config()

    def read(self, reason: str) -> str:
        """A method called by SimpleServer when a PV is read from the BlockServer over
         Channel Access.

        Args:
            reason (string): The PV that is being requested (without the PV prefix)

        Returns:
            string : A compressed and hexed JSON formatted string that gives the desired
            information based on reason.
            If an Exception is thrown in the reading of the information this is returned
             in compressed and hexed JSON.
        """
        try:
            if reason == BlockserverPVNames.GROUPS:
                grps = ConfigurationJsonConverter.groups_to_json(
                    self._active_configserver.get_group_details()
                )
                value = compress_and_hex(grps)
            elif reason == BlockserverPVNames.CONFIGS:
                value = compress_and_hex(convert_to_json(self._config_list.get_configs()))
            elif reason == BlockserverPVNames.COMPS:
                value = compress_and_hex(convert_to_json(self._config_list.get_components()))
            elif reason == BlockserverPVNames.BLANK_CONFIG:
                js = convert_to_json(self.get_blank_config())
                value = compress_and_hex(js)
            elif reason == BlockserverPVNames.BANNER_DESCRIPTION:
                value = compress_and_hex(self.spangle_banner)
            elif reason == BlockserverPVNames.ALL_COMPONENT_DETAILS:
                value = compress_and_hex(
                    convert_to_json(list(self._config_list.all_components.values()))
                )
            elif reason == BlockserverPVNames.CURR_CONFIG_NAME:
                value = self._active_configserver.get_config_name()
            elif reason == BlockserverPVNames.CURR_CONFIG_NAME_SEVR:
                value = CURR_CONFIG_NAME_SEVR_VALUE
            elif reason == BlockserverPVNames.HEARTBEAT:
                value = 0
            else:
                # Check to see if it is a on-the-fly PV
                for handler in self.on_the_fly_handlers:
                    if handler.read_pv_exists(reason):
                        return handler.handle_pv_read(reason)

                value = self.getParam(reason)
        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "MAJOR")
        return value

    def write(self, reason: str, value: str) -> str:
        """A method called by SimpleServer when a PV is written to the BlockServer over
         Channel Access. The write commands are queued as Channel Access is single-threaded.

        Args:
            reason (string): The PV that is being requested (without the PV prefix)
            value (string): The data being written to the 'reason' PV

        Returns:
            string : "OK" in compressed and hexed JSON if function succeeds.
             Otherwise returns the Exception in compressed and hexed JSON.
        """
        status = True
        try:
            data = dehex_and_decompress(bytes(value, encoding="utf-8")).strip(b'"').decode("utf-8")
            if reason == BlockserverPVNames.LOAD_CONFIG:
                self.write_queue.put((self.load_config, (data,), "LOADING_CONFIG"))
            elif reason == BlockserverPVNames.RELOAD_CURRENT_CONFIG:
                self.write_queue.put((self.reload_current_config, (), "RELOAD_CURRENT_CONFIG"))
            elif reason == BlockserverPVNames.START_IOCS:
                self.write_queue.put((self.start_iocs, (convert_from_json(data),), "START_IOCS"))
            elif reason == BlockserverPVNames.STOP_IOCS:
                self.write_queue.put(
                    (self._ioc_control.stop_iocs, (convert_from_json(data),), "STOP_IOCS")
                )
            elif reason == BlockserverPVNames.RESTART_IOCS:
                self.write_queue.put(
                    (
                        self._ioc_control.restart_iocs,
                        (convert_from_json(data), True),
                        "RESTART_IOCS",
                    )
                )
            elif reason == BlockserverPVNames.SET_CURR_CONFIG_DETAILS:
                self.write_queue.put((self._set_curr_config, (data,), "SETTING_CONFIG"))
            elif reason == BlockserverPVNames.SAVE_NEW_CONFIG:
                self.write_queue.put((self.save_config, (data,), "SAVING_NEW_CONFIG"))
            elif reason == BlockserverPVNames.SAVE_NEW_COMPONENT:
                self.write_queue.put((self.save_config, (data, True), "SAVING_NEW_COMP"))
            elif reason == BlockserverPVNames.DELETE_CONFIGS:
                self.write_queue.put(
                    (self._config_list.delete_configs, (convert_from_json(data),), "DELETE_CONFIGS")
                )
            elif reason == BlockserverPVNames.DELETE_COMPONENTS:
                self.write_queue.put(
                    (
                        self._config_list.delete_components,
                        (convert_from_json(data),),
                        "DELETE_COMPONENTS",
                    )
                )
            else:
                status = False
                # Check to see if it is a on-the-fly PV
                for handler in self.on_the_fly_handlers:
                    if handler.write_pv_exists(reason):
                        self.write_queue.put(
                            (handler.handle_pv_write, (reason, data), "SETTING_CONFIG")
                        )
                        status = True
                        break

        except Exception as err:
            value = compress_and_hex(convert_to_json("Error: " + str(err)))
            print_and_log(str(err), "MAJOR")
        else:
            if status:
                value = compress_and_hex(convert_to_json("OK"))

        # store the values
        if status:
            self.setParam(reason, value)
        return status

    def load_last_config(self) -> None:
        """Loads the last configuration used.

        The information is saved in a text file.
        """
        last = self._active_configserver.load_last_config()
        if last is None:
            print_and_log("Could not retrieve last configuration - starting blank configuration")
            self._active_configserver.clear_config()
        else:
            print_and_log("Loaded last configuration: %s" % last)
        self._initialise_config()

    def _set_curr_config(self, details: str) -> None:
        """Sets the current configuration details to that defined in the JSON, saves to disk,
        then re-initialises the current configuration.

        Args:
            details (string): the configuration JSON
        """

        current_name = self._active_configserver.get_config_name()
        details_name = convert_from_json(details)["name"]

        # This method saves the given details and then reloads the current config.
        # Sending the details of a new config to this method, as was being done incorrectly
        # (see #4606)
        # will save the details as a new config, but not load it.
        # A warning is sent in case this happens again.
        if current_name != details_name:
            print_and_log(
                f"Config details to be set ({details_name}) did "
                f"not match current config ({current_name})",
                "MINOR",
            )

        self.save_config(details)

    def _initialise_config(self, full_init: bool = False) -> None:
        """Responsible for initialising the configuration.
        Sets all the monitors, initialises the gateway, etc.

        Args:
            full_init (bool, optional): whether this requires a full initialisation,
             e.g. on loading a new configuration
        """
        new_iocs, changed_iocs, removed_iocs = self._active_configserver.iocs_changed()

        self._ioc_control.stop_iocs(removed_iocs)
        self._start_config_iocs(new_iocs, changed_iocs)

        if (
            CAEN_DISCRIMINATOR_IOC_NAME in self._active_configserver.get_ioc_names()
            and CAEN_DISCRIMINATOR_IOC_NAME not in new_iocs
        ):
            # See https://github.com/ISISComputingGroup/IBEX/issues/5590 for justification of why
            # this ioc gets special treatment.
            ioc = self._active_configserver.get_all_ioc_details()[CAEN_DISCRIMINATOR_IOC_NAME]
            if ioc.autostart:
                print_and_log(
                    f"{CAEN_DISCRIMINATOR_IOC_NAME} present in configuration and set "
                    f"to autostart - restarting it"
                )
                if self._ioc_control.get_ioc_status(CAEN_DISCRIMINATOR_IOC_NAME) == "RUNNING":
                    self._ioc_control.restart_iocs([CAEN_DISCRIMINATOR_IOC_NAME], reapply_auto=True)
                else:
                    self.start_iocs([CAEN_DISCRIMINATOR_IOC_NAME])

        # Set up the gateway
        if self._active_configserver.blocks_changed() or full_init:
            self._gateway.set_new_aliases(
                self._active_configserver.get_block_details(),
                self._active_configserver.configures_block_gateway_and_archiver(),
                os.path.join(
                    CONFIG_DIR, "configurations", self._active_configserver.get_config_name()
                ),
            )

        self._config_list.active_config_name = self._active_configserver.get_config_name()
        self._config_list.active_components = self._active_configserver.get_component_names()
        self._config_list.update_monitors()

        self.update_blocks_monitors()

        self.update_get_details_monitors()
        self.update_wd_details_monitors()
        self.update_curr_config_name_monitors()
        self._active_configserver.update_archiver(full_init)
        for handler in self.on_the_fly_handlers:
            handler.on_config_change(full_init=full_init)

        # Update Web Server text
        self.server.set_config(convert_to_json(self._active_configserver.get_config_details()))
        self.write_queue.put((self.set_config_block_values, (), "LOADING_BLOCK_SETS"))

    def _start_config_iocs(self, iocs_to_start: list[str], iocs_to_restart: list[str]) -> None:
        # Start the IOCs, if they are available and if they are flagged for autostart
        # Note: autostart means the IOC is started when the config is loaded,
        # restart means the IOC should automatically restart if it stops for some reason
        # (e.g. it crashes)
        def _ioc_from_name(ioc_name: str) -> str:
            return self._active_configserver.get_all_ioc_details()[ioc_name]

        def _is_remote(ioc_name: str) -> bool:
            return _ioc_from_name(ioc_name).remotePvPrefix not in (None, "")

        def _should_start(ioc_name: str) -> bool:
            ioc = _ioc_from_name(ioc_name)
            return ioc.autostart and not _is_remote(ioc_name)

        self._ioc_control.start_iocs([ioc for ioc in iocs_to_start if _should_start(ioc)])
        self._ioc_control.restart_iocs([ioc for ioc in iocs_to_restart if _should_start(ioc)])

        for ioc in iocs_to_start:
            self._ioc_control.waitfor_running(ioc)
            self._ioc_control.set_autorestart(ioc, _ioc_from_name(ioc).restart)

        for ioc in iocs_to_restart:
            self._ioc_control.waitfor_running(ioc)
            self._ioc_control.set_autorestart(ioc, _ioc_from_name(ioc).restart)

        # If an IOC is told to restart but autostart was not set, then it should be stopped instead.
        # This doesn't apply to remote IOCs, who are controlled by the RemoteIOCServer instead.
        self._ioc_control.stop_iocs(
            [
                ioc
                for ioc in iocs_to_restart
                if not _ioc_from_name(ioc).autostart and not _is_remote(ioc)
            ]
        )

    def load_config(self, config: str, full_init: bool = True) -> None:
        """Load a configuration.

        Args:
            config (string): The name of the configuration
            full_init (bool): True to restart all IOCs/services or False to
             restart only those required
        """
        print_and_log(f"Loading configuration '{config}'")
        try:
            self._active_configserver.load_active(config)
            # If we get this far then assume the config is okay
            self._initialise_config(full_init=full_init)
        except Exception as err:
            print_and_log(f"Exception while loading configuration '{config}': {err}", "MAJOR")
            traceback.print_exc()

    def reload_current_config(self) -> None:
        """Reload the current configuration."""
        try:
            print_and_log("Reloading current configuration")
            self._active_configserver.reload_current_config()
            self._initialise_config(full_init=True)
        except Exception as err:
            print_and_log(
                "Exception while reloading current configuration: {}".format(err), "MAJOR"
            )
            traceback.print_exc()

    def save_config(self, json_data: str, as_comp: bool = False) -> None:
        """Save a configuration.

        Args:
            json_data (string): The JSON data containing the configuration/component
            as_comp (bool): Whether it is a component or not
        """
        new_details = convert_from_json(json_data)

        config_name = new_details["name"]

        new_config_is_protected = new_details.get("isProtected", False)

        # Is the config we've been sent marked with the "protected" flag?
        if new_config_is_protected:
            verify_manager_mode(
                message="Attempt to save protected {} ('{}')".format(
                    "component" if as_comp else "config", config_name
                )
            )

        inactive = InactiveConfigHolder(MACROS, ConfigurationFileManager())

        # Is the config we're overwriting (if any) marked with the protected flag?
        try:
            inactive.load_inactive(new_details["name"], is_component=as_comp)
            if inactive.is_protected():
                verify_manager_mode(
                    message="Attempt to overwrite protected {} ('{}')".format(
                        "component" if as_comp else "config", config_name
                    )
                )
        except IOError:
            pass  # IOError thrown if config we're overwriting didn't exist, i.e.
            # this is a brand new config/component.

        history = self._get_inactive_history(config_name, as_comp)

        inactive.set_config_details(new_details)

        # Set updated history
        history.append(self._get_timestamp())
        inactive.set_history(history)

        try:
            if not as_comp:
                print_and_log(f"Saving configuration ({config_name})")
                inactive.save_inactive()
                self._config_list.update_a_config_in_list(inactive)
            else:
                print_and_log(f"Saving component ({config_name})")
                inactive.save_inactive(as_comp=True)
                self._config_list.update_a_config_in_list(inactive, True)

            print_and_log(f"Finished saving ({config_name})")

        except Exception:
            print_and_log(
                f"Problem occurred saving configuration: {traceback.format_exc()}", "MAJOR"
            )

        # Reload configuration if a component has changed
        if as_comp and new_details["name"] in self._active_configserver.get_component_names():
            self.load_last_config()

        # If the configuration we are trying to save is the currently active one,
        # we need to reload it.
        if config_name == self._active_configserver.get_config_name():
            self.load_config(config_name, full_init=False)

    def _get_inactive_history(self, name: str, is_component: bool = False) -> list[str | None]:
        # If it already exists load it
        try:
            inactive = InactiveConfigHolder(MACROS, ConfigurationFileManager())
            inactive.load_inactive(name, is_component)
            # Get previous history
            history = inactive.get_history()
        except IOError:
            # Config doesn't exist therefore start new history
            history = list()
        return history

    def _get_timestamp(self) -> str:
        return datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")

    def update_blocks_monitors(self) -> None:
        """Updates the PV monitors for the blocks and groups, so the clients can see any changes."""
        with self.monitor_lock:
            block_names = convert_to_json(self._active_configserver.get_blocknames())
            self.setParam(BlockserverPVNames.BLOCKNAMES, compress_and_hex(block_names))

            groups = ConfigurationJsonConverter.groups_to_json(
                self._active_configserver.get_group_details()
            )
            self.setParam(BlockserverPVNames.GROUPS, compress_and_hex(groups))

            self.updatePVs()

    def update_server_status(self, status: str = "") -> None:
        """Updates the monitor for the server status, so the clients can see any changes.

        Args:
            status (string): The status to set
        """
        if self._active_configserver is not None:
            with self.monitor_lock:
                self.setParam(
                    BlockserverPVNames.SERVER_STATUS,
                    compress_and_hex(convert_to_json({"status": status})),
                )
                self.updatePVs()

    def update_get_details_monitors(self) -> None:
        """Updates the monitor for the active configuration, so the clients can see any changes."""
        with self.monitor_lock:
            config_details_json = convert_to_json(self._active_configserver.get_config_details())
            self.setParam(
                BlockserverPVNames.GET_CURR_CONFIG_DETAILS, compress_and_hex(config_details_json)
            )
            self.updatePVs()

    def update_wd_details_monitors(self) -> None:
        """Updates the monitor for the active configuration,
        so the web dashboard can see any changes."""
        with self.monitor_lock:
            config_details_json = convert_to_json(
                {
                    k: v
                    for k, v in self._active_configserver.get_config_details().items()
                    if k not in ["component_iocs", "iocs"]
                }
            )
            self.setParam(BlockserverPVNames.WD_CONF_DETAILS, compress_and_hex(config_details_json))
            self.updatePVs()

    def update_curr_config_name_monitors(self) -> None:
        """Updates the monitor for the active configuration name,
        so the clients can see any changes."""
        with self.monitor_lock:
            self.setParam(
                BlockserverPVNames.CURR_CONFIG_NAME, self._active_configserver.get_config_name()
            )
            self.setParam(BlockserverPVNames.CURR_CONFIG_NAME_SEVR, CURR_CONFIG_NAME_SEVR_VALUE)
            self.updatePVs()

    def consume_write_queue(self) -> None:
        """Actions any requests on the write queue.

        Queue items are tuples with three values:
        the method to call; the argument(s) to send (tuple);
         and, the description of the state (string))

        For example:
            self.load_config, ("configname",), "LOADING_CONFIG")
        """
        while True:
            cmd, arg, state = self.write_queue.get(block=True)
            self.update_server_status(state)
            try:
                cmd(*arg) if arg is not None else cmd()
            except ManagerModeRequiredError as err:
                print_and_log(f"Error, operation requires manager mode: {err}", "MAJOR")
            except Exception as err:
                print_and_log(
                    f"Error executing write queue command {cmd.__name__} for state {state}: {err}",
                    "MAJOR",
                )
                traceback.print_exc()
            self.update_server_status("")

    def get_blank_config(self) -> Dict[str, Any]:
        """Get a blank configuration which can be used to create a new configuration from scratch.

        Returns:
            dict : A dictionary containing all the details of a blank configuration
        """
        temp_config = InactiveConfigHolder(MACROS, ConfigurationFileManager())
        return temp_config.get_config_details()

    def start_iocs(self, iocs: list[str]) -> None:
        # If the IOC is in the config and auto-restart is set to true then
        # reapply the auto-restart setting after starting.
        # This is because stopping an IOC via procServ turns auto-restart off.
        conf_iocs = self._active_configserver.get_all_ioc_details()

        # Request IOCs to start
        for i in iocs:
            self._ioc_control.start_ioc(i)

        # Once all IOC start requests issued, wait for running and apply auto restart as needed
        for i in iocs:
            if i in conf_iocs and conf_iocs[i].restart:
                if conf_iocs[i].remotePvPrefix not in (None, ""):
                    print_and_log(f"IOC '{i}' is set to run remotely - not applying auto-restart.")
                    continue
                # Give it time to start as IOC has to be running to be able to set restart property
                print(f"Re-applying auto-restart setting to {i}")
                self._ioc_control.waitfor_running(i)
                self._ioc_control.set_autorestart(i, True)

    # Code for handling on-the-fly PVs
    def does_pv_exist(self, name: str) -> bool:
        return name in manager.pvs[self.port]

    # Code for handling block-sets
    def set_config_block_values(self) -> None:
        blocks = {
            block_details
            for block_details in self._active_configserver.get_block_details().values()
            if block_details.set_block
        }
        start = time()
        timeout = 30
        prefix = MACROS[PVPREFIX_MACRO]
        for block_details in blocks:
            pv = f"{prefix}{block_details.pv}"
            while not ChannelAccess.pv_exists(pv):
                sleep(0.5)
                if time() - start >= timeout:
                    print_and_log(
                        f"Gave up waiting for block {block_details.name},"
                        f" {block_details.pv} to exist",
                        "MAJOR",
                    )
                    break
            # check for existence of set-point pv
            pv_with_setpoint = f"{pv}:SP"
            if ChannelAccess.pv_exists(pv_with_setpoint):
                ChannelAccess.caput(pv_with_setpoint, block_details.set_block_val)
            else:
                ChannelAccess.caput(pv, block_details.set_block_val)

    def delete_pv_from_db(self, name: str) -> None:
        if name in manager.pvs[self.port]:
            print_and_log(f"Removing PV {name}")
            fullname = manager.pvs[self.port][name].name
            del manager.pvs[self.port][name]
            del manager.pvf[fullname]
            del self.pvDB[name]

    def add_string_pv_to_db(self, name: str, count: int = 1000) -> None:
        # Check name not already in PVDB and that a PV does not already exist
        if name not in manager.pvs[self.port]:
            try:
                print_and_log(f"Adding PV {name}")
                new_pv = {name: char_waveform(count)}
                self._cas.createPV(CONTROL_SYSTEM_PREFIX, new_pv)
                data = Data()
                data.value = manager.pvs[self.port][name].info.value
                self.pvDB[name] = data
            except Exception:
                print_and_log(f"Unable to add PV {name}", "MAJOR")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-cd",
        "--config_dir",
        nargs=1,
        type=str,
        default=["."],
        help="The directory from which to load the configuration (default=current directory)",
    )
    parser.add_argument(
        "-scd",
        "--script_dir",
        nargs=1,
        type=str,
        default=["."],
        help="The directory in which instrument scripts are stored",
    )
    parser.add_argument(
        "-sd",
        "--schema_dir",
        nargs=1,
        type=str,
        help="Directory from which to load the configuration schema (default=server_common)",
    )
    parser.add_argument(
        "-od",
        "--options_dir",
        nargs=1,
        type=str,
        default=["."],
        help="Directory from which to load the configuration options(default=current directory)",
    )
    parser.add_argument(
        "-g",
        "--gateway_prefix",
        nargs=1,
        type=str,
        default=[MACROS["$(MYPVPREFIX)"] + "CS:GATEWAY:BLOCKSERVER"],
        help="The prefix for the blocks gateway (default="
        + MACROS["$(MYPVPREFIX)"]
        + "CS:GATEWAY:BLOCKSERVER)",
    )
    parser.add_argument(
        "-pv",
        "--pvlist_name",
        nargs=1,
        type=str,
        default=["gwblock.pvlist"],
        help="The filename for the pvlist file used by the blocks gateway (default=gwblock.pvlist)",
    )
    parser.add_argument(
        "-au",
        "--archive_uploader",
        nargs=1,
        default=[
            os.path.join(
                MACROS["$(EPICS_KIT_ROOT)"],
                "CSS",
                "master",
                "ArchiveEngine",
                "set_block_config.bat",
            )
        ],
        help="The batch file used to upload settings to the PV Archiver",
    )
    parser.add_argument(
        "-as",
        "--archive_settings",
        nargs=1,
        default=[
            os.path.join(
                MACROS["$(EPICS_KIT_ROOT)"], "CSS", "master", "ArchiveEngine", "block_config.xml"
            )
        ],
        help="The XML file containing the new PV Archiver log settings",
    )
    parser.add_argument(
        "-f",
        "--facility",
        nargs=1,
        type=str,
        default=["ISIS"],
        help="Which facility is this being run for (default=ISIS)",
    )

    args = parser.parse_args()

    FACILITY = args.facility[0]
    if FACILITY == "ISIS":
        from server_common.loggers.isis_logger import IsisLogger

        set_logger(IsisLogger())
    print_and_log(f"FACILITY = {FACILITY}")

    GATEWAY_PREFIX = args.gateway_prefix[0]
    if not GATEWAY_PREFIX.endswith(":"):
        GATEWAY_PREFIX += ":"
    GATEWAY_PREFIX = GATEWAY_PREFIX.replace("%MYPVPREFIX%", MACROS["$(MYPVPREFIX)"])
    print_and_log(f"BLOCK GATEWAY PREFIX = {GATEWAY_PREFIX}")

    CONFIG_DIR = os.path.abspath(args.config_dir[0])
    print_and_log(f"CONFIGURATION DIRECTORY {CONFIG_DIR}")

    SCRIPT_DIR = os.path.abspath(args.script_dir[0])
    print_and_log(f"SCRIPTS DIRECTORY {SCRIPT_DIR}")

    if not args.schema_dir:
        schema_cm = as_file(files("server_common.schema"))
    else:
        schema_cm = contextlib.nullcontext(args.schema_dir[0])

    with schema_cm as schema_dir:
        SCHEMA_DIR = schema_dir
        print_and_log(f"SCHEMA DIRECTORY = {SCHEMA_DIR}")

        ARCHIVE_UPLOADER = args.archive_uploader[0].replace(
            "%EPICS_KIT_ROOT%", MACROS["$(EPICS_KIT_ROOT)"]
        )
        print_and_log(f"ARCHIVE UPLOADER = {ARCHIVE_UPLOADER}")

        ARCHIVE_SETTINGS = args.archive_settings[0].replace(
            "%EPICS_KIT_ROOT%", MACROS["$(EPICS_KIT_ROOT)"]
        )
        print_and_log(f"ARCHIVE SETTINGS = {ARCHIVE_SETTINGS}")

        PVLIST_FILE = args.pvlist_name[0]

        print_and_log(f"BLOCKSERVER PREFIX = {CONTROL_SYSTEM_PREFIX}")
        SERVER = SimpleServer()
        SERVER.createPV(CONTROL_SYSTEM_PREFIX, initial_dbs)
        DRIVER = BlockServer(SERVER)  # pyright: ignore

        # Process CA transactions
        while True:
            try:
                SERVER.process(0.1)
            except Exception as err:
                print_and_log(err, "MAJOR")
                break
