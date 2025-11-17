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

"""Contains the code for the ConfigHolder class"""

import copy
import re
from collections import OrderedDict
from typing import Any, Dict, List

from server_common.file_path_manager import FILEPATH_MANAGER
from server_common.helpers import PVPREFIX_MACRO
from server_common.utilities import print_and_log

from BlockServer.config.configuration import Configuration
from BlockServer.config.group import Group
from BlockServer.config.metadata import MetaData
from BlockServer.core.constants import DEFAULT_COMPONENT, GRP_NONE
from BlockServer.fileIO.file_manager import ConfigurationFileManager


class ConfigHolder:
    """The ConfigHolder class.

    Holds a configuration which can then be manipulated via this class.
    """

    def __init__(
        self,
        macros: Dict,
        file_manager: ConfigurationFileManager,
        is_component: bool = False,
        test_config: Configuration = None,
    ) -> None:
        """Constructor.

        Args:
            macros: The dictionary containing the macros
            is_component: Defines whether the configuration held is a component or not
            file_manager: The object used to save the configuration
            test_config: A dummy configuration used for the unit tests :o(
        """
        if test_config is None:
            self._config = Configuration(macros)
        else:
            self._config = test_config
        self._components = OrderedDict()
        self._is_component = is_component
        self._macros = macros

        self._config_path = FILEPATH_MANAGER.config_dir
        self._component_path = FILEPATH_MANAGER.component_dir
        self._filemanager = file_manager

        self._cached_config = Configuration(macros)
        self._cached_components = OrderedDict()

    def clear_config(self) -> None:
        """Clears the configuration."""
        self._config = Configuration(self._macros)
        self._components = OrderedDict()
        self._is_component = False

    def add_component(self, name: str) -> None:
        """Add a component with the specified name to the configuration.

        Args:
            name: The name of the component being added
        """
        # Add it to the holder
        if self._is_component:
            raise ValueError("Can not add a component to a component")

        component = self.load_configuration(name, True)

        if name.lower() not in self._components:
            # Add it
            component.set_name(name)
            self._components[name.lower()] = component
            self._config.components[name.lower()] = name  # Only needs its case sensitive name name
        else:
            raise ValueError(
                "Requested component is already part of the configuration: " + str(name)
            )

    def remove_comp(self, name: str) -> None:
        """Removes a component from the configuration.

        This is not needed as part of the BlockServer as such, but it helps with unit testing.

        Args:
            name: The name of the component to remove
        """
        # Remove it from the holder
        if self._is_component:
            raise ValueError("Can not remove a component from a component")
        del self._components[name.lower()]
        del self._config.components[name.lower()]

    def get_blocknames(self) -> List[str]:
        """Get all the blocknames including those in the components.

        Returns:
            The names of all the blocks
        """
        names = []
        for block in self._config.blocks.values():
            names.append(block.name)

        for component in self._components.values():
            for block in component.blocks.values():
                # Ignore duplicates
                if block.name not in names:
                    names.append(block.name)
        return names

    def get_block_details(self):
        """Get the configuration details for all the blocks including any in components.

        Returns:
            A dictionary of block objects
        """
        blocks = copy.deepcopy(self._config.blocks)
        for component in self._components.values():
            for block_name, block in component.blocks.items():
                if block_name not in blocks:
                    blocks[block_name] = block
        return blocks

    def get_group_details(self) -> Dict[str, Group]:
        """Get the groups details for all the groups including any in components.

        Returns:
            A dictionary of group objects
        """
        blocks = self.get_blocknames()
        used_blocks = []
        groups = copy.deepcopy(self._config.groups)

        for group in groups.values():
            used_blocks.extend(group.blocks)

        for component in self._components.values():
            for group_name, grp in component.groups.items():
                if group_name not in groups.keys():
                    # Add the groups if they have not been used before and exist
                    blks = [x for x in grp.blocks if x not in used_blocks and x in blocks]
                    groups[group_name] = grp
                    groups[group_name].blocks = blks
                    used_blocks.extend(blks)
                else:
                    # If group exists then append with component group
                    # But don't add any duplicate blocks or blocks that don't exist
                    for bn in grp.blocks:
                        if (
                            bn not in groups[group_name].blocks
                            and bn not in used_blocks
                            and bn in blocks
                        ):
                            groups[group_name].blocks.append(bn)
                            used_blocks.append(bn)

        # If any groups are empty now we've filled in from the components, get rid of them
        # This is an ordered dict so we need to copy it before iterating - throws a runtime error
        # if it has mutated.
        groups_copy = groups.copy()
        for key in groups_copy.keys():
            if len(groups[key].blocks) == 0:
                groups.pop(key)

        return groups

    def _set_group_details(self, redefinition) -> None:
        # Any redefinition only affects the main configuration
        homeless_blocks = self.get_blocknames()
        for grp in redefinition:
            # Skip the NONE group
            if grp["name"].lower() == GRP_NONE.lower():
                continue
            # If the group is in the config then it can be changed completely
            if grp["name"].lower() in self._config.groups:
                if len(grp["blocks"]) == 0 and grp["component"] is None:
                    # No blocks so delete the group
                    del self._config.groups[grp["name"].lower()]
                    continue
                self._config.groups[grp["name"].lower()].blocks = []
                for blk in grp["blocks"]:
                    if blk in homeless_blocks:
                        self._config.groups[grp["name"].lower()].blocks.append(blk)
                        homeless_blocks.remove(blk)
            else:
                component = grp.get("component")
                # Ignore empty groups, except those with components. Component groups are
                # included just for ordering
                if len(grp["blocks"]) > 0 or component is not None:
                    self._config.groups[grp["name"].lower()] = Group(
                        grp["name"], component=component
                    )
                    if component is None:
                        for blk in grp["blocks"]:
                            if blk in homeless_blocks:
                                self._config.groups[grp["name"].lower()].blocks.append(blk)
                                homeless_blocks.remove(blk)
        # Finally, anything in homeless gets put in NONE
        if GRP_NONE.lower() not in self._config.groups:
            self._config.groups[GRP_NONE.lower()] = Group(GRP_NONE)
        self._config.groups[GRP_NONE.lower()].blocks = homeless_blocks

    def get_config_name(self) -> str:
        """Get the name of the configuration.

        Returns:
            The name
        """
        return self._config.get_name()

    def _set_config_name(self, name: str) -> None:
        self._config.set_name(name)

    def get_ioc_names(self, include_base: bool = False) -> List[str]:
        """Get the names of the IOCs in the configuration and any components.

        Args:
            include_base: Whether to include the IOCs in base

        Returns:
            The names of the IOCs
        """
        iocs = list(self._config.iocs.keys())
        for cn, cv in self._components.items():
            if include_base or cn.lower() != DEFAULT_COMPONENT.lower():
                iocs.extend(cv.iocs)
        return iocs

    def get_ioc_details(self):
        """Get the details of the IOCs in the configuration.

        Returns:
            A copy of all the configuration IOC details
        """
        return copy.deepcopy(self._config.iocs)

    def get_component_ioc_details(self):
        """Get the details of the IOCs in any components.

        Returns:
            A copy of all the component IOC details
        """
        iocs = {}
        for component in self._components.values():
            for ioc_name, ioc in component.iocs.items():
                if ioc_name not in iocs:
                    iocs[ioc_name] = ioc
        return iocs

    def get_all_ioc_details(self):
        """Get the details of the IOCs in the configuration and any components.

        Returns:
            A copy of all the IOC details
        """
        iocs = self.get_ioc_details()
        iocs.update(self.get_component_ioc_details())
        return iocs

    def get_component_names(self, include_base: bool = False) -> List[str]:
        """Get the names of the components in the configuration.

        Args:
            include_base: Whether to include the base in the list of names

        Returns:
            A list of components in the configuration
        """
        component_names = []
        for component_name, component in self._components.items():
            if include_base or (component_name.lower() != DEFAULT_COMPONENT.lower()):
                component_names.append(component.get_name())
        return component_names

    def add_block(self, blockargs: Dict) -> None:
        """Add a block to the configuration.

        Args:
            blockargs: A dictionary of settings for the new block
        """
        self._config.add_block(**blockargs)

    def _add_ioc(
        self,
        name: str,
        component: str | None = None,
        autostart: bool = True,
        restart: bool = True,
        macros: Dict | None = None,
        pvs: Dict | None = None,
        pvsets: Dict | None = None,
        simlevel: str | None = None,
        remotePvPrefix: str | None = None,  # noqa: N803
    ) -> None:
        # TODO: use IOC object instead?
        if component is None:
            self._config.add_ioc(
                name, None, autostart, restart, macros, pvs, pvsets, simlevel, remotePvPrefix
            )
        elif component.lower() in self._components:
            self._components[component.lower()].add_ioc(
                name, component, autostart, restart, macros, pvs, pvsets, simlevel, remotePvPrefix
            )
        else:
            raise ValueError(
                f"Can't add IOC '{name}' to component '{component}': component does not exist"
            )

    def _globalmacros_to_list(self):
        print_and_log(f"Retrieving cached _globalmacros_to_list...size is '{len(self._config.globalmacros)}'")
        #globalmacros = []
        #for iocname, globalmacro in self._config.globalmacros:
        #    globalmacros.append(b)
        #return globalmacros
        #return copy.deepcopy(self._config.globalmacros)
        #return self._config.globalmacros
        return [globalmacro.to_dict() for globalmacro in self._config.globalmacros.values()]

    def get_config_details(self) -> Dict[str, Any]:
        """Get the details of the configuration.

        Returns:
            A dictionary containing all the details of the configuration
        """
        return {
            "globalmacros": self._globalmacros_to_list(),
            "blocks": self._blocks_to_list(True),
            "groups": self._groups_to_list(),
            "iocs": self._iocs_to_list(),
            "component_iocs": self._iocs_to_list_with_components(),
            "components": self._comps_to_list(),  # Just return the names of the components
            "name": self._config.get_name(),
            "description": self._config.meta.description,
            "synoptic": self._config.meta.synoptic,
            "history": self._config.meta.history,
            "isProtected": self._config.meta.isProtected,
            "isDynamic": self._config.meta.isDynamic,
            "configuresBlockGWAndArchiver": self._config.meta.configuresBlockGWAndArchiver,
        }

    def is_protected(self) -> bool:
        """
        Whether this config has been marked as "protected" or not.

        Returns:
            Whether the configuration is protected.
        """
        return self._config.meta.isProtected

    def is_dynamic(self) -> bool:
        """
        Whether this config has been marked as "dynamic" or not.

        Returns:
            Whether the configuration is dynamic.
        """
        return self._config.meta.isDynamic

    def configures_block_gateway_and_archiver(self):
        """
        Returns:
            (bool): Whether this config has a gwblock.pvlist and block_config.xml to configure the
             block gateway and archiver with.
        """
        return self._config.meta.configuresBlockGWAndArchiver

    def _comps_to_list(self):
        comps = []
        for component_name, component_value in self._components.items():
            if component_name.lower() != DEFAULT_COMPONENT.lower():
                comps.append({"name": component_value.get_name()})
        return comps

    def _blocks_to_list(self, expand_macro: bool = False):
        blocks = self.get_block_details()
        blks = []
        if blocks is not None:
            for block in blocks.values():
                b = block.to_dict()
                if expand_macro or b["local"]:
                    # Replace the prefix
                    b["pv"] = b["pv"].replace(PVPREFIX_MACRO, self._macros[PVPREFIX_MACRO])
                blks.append(b)
        return blks

    def _groups_to_list(self):
        groups = self.get_group_details()
        grps = []
        if groups is not None:
            for group in groups.values():
                if group.name.lower() != GRP_NONE.lower():
                    grps.append(group.to_dict())

            # Add NONE group at end
            if GRP_NONE.lower() in groups.keys():
                grps.append(groups[GRP_NONE.lower()].to_dict())
        return grps

    def _iocs_to_list(self):
        return [ioc.to_dict() for ioc in self._config.iocs.values()]

    def _iocs_to_list_with_components(self):
        ioc_list = self._iocs_to_list()

        for component in self._components.values():
            for ioc in component.iocs.values():
                ioc_list.append(ioc.to_dict())
        return ioc_list

    def _to_dict(self, data_list):
        return None if data_list is None else {item["name"]: item for item in data_list}

    def set_config(self, config: Configuration, is_component: bool = False) -> None:
        """Replace the existing configuration with the supplied configuration.

        Args:
            config: A configuration
            is_component: Whether it is a component
        """
        self._cache_config()
        self.clear_config()
        self._config = config
        self._is_component = is_component
        self._components = OrderedDict()
        if not is_component:
            for n, v in config.components.items():
                if n.lower() != DEFAULT_COMPONENT.lower():
                    self.add_component(v)
            # add default component to list of components
            self.add_component(DEFAULT_COMPONENT)

    def _set_component_names(self, comp: Configuration, name: str) -> None:
        # Set the component for blocks, groups and IOCs
        for block in comp.blocks.values():
            block.component = name
        for group in comp.groups.values():
            group.component = name
        for ioc in comp.iocs.values():
            ioc.component = name

    def load_configuration(
        self, name: str, is_component: bool = False, set_component_names: bool = True
    ) -> Configuration:
        """Load a configuration.

        Args:
            name: The name of the configuration to load
            is_component: Whether it is a component
            set_component_names: Whether to set the component names
        """
        if is_component:
            comp = self._filemanager.load_config(name, self._macros, True)
            if set_component_names:
                self._set_component_names(comp, name)
            return comp
        else:
            return self._filemanager.load_config(name, self._macros, False)

    def save_configuration(self, name: str, as_component: bool) -> None:
        """Save the configuration.

        Args:
            name: The name to save the configuration under
            as_component: Whether to save as a component
        """
        self._check_name(name, as_component)
        if self._is_component != as_component:
            self._set_as_component(as_component)

        if self._is_component:
            self._set_config_name(name)
            self._filemanager.save_config(self._config, True)
        else:
            self._set_config_name(name)
            # TODO: CHECK WHAT COMPONENTS self._config contains and remove _base if it is in there
            self._filemanager.save_config(self._config, False)

    def _check_name(self, name: str, is_comp: bool = False) -> None:
        # Not empty
        if name is None or name.strip() == "":
            raise ValueError("Configuration name cannot be blank")

        if is_comp and name.lower() == DEFAULT_COMPONENT.lower():
            raise ValueError("Cannot save over default component")
        # Valid chars
        m = re.match("^[a-zA-Z][a-zA-Z0-9_]*$", name)
        if m is None:
            raise ValueError("Configuration name contains invalid characters")

    def _set_as_component(self, value: bool) -> None:
        if value is True:
            if len(self._components) == 0:
                self._is_component = True
            else:
                raise ValueError(
                    "Can not cast to a component as the configuration contains at least one "
                    "component"
                )

            # Strip out any remaining groups that belong to components
            for key in self._config.groups:
                if self._config.groups[key].component is not None:
                    del self._config.groups[key]
        else:
            self._is_component = False

    def _cache_config(self) -> None:
        self._cached_config = copy.deepcopy(self._config)
        self._cached_components = copy.deepcopy(self._components)

    def _retrieve_cache(self) -> None:
        print_and_log("Retrieving cached configuration...")
        self._config = copy.deepcopy(self._cached_config)
        self._components = copy.deepcopy(self._cached_components)

    def get_config_meta(self) -> MetaData:
        """Fetch the configuration's metadata.

        Returns:
            MetaData : The metadata for the configuration
        """
        return self._config.meta

    def get_cached_name(self) -> str:
        """Get the previous name which may be the same as the current.

        Returns:
            string : The previous name
        """
        return self._cached_config.get_name()

    def set_history(self, history: List[str | None]) -> None:
        """Set history for configuration.

        Args:
            history (list): The new history
        """
        self._config.meta.history = history

    def get_history(self) -> List[str | None]:
        """Get the history for configuration.

        Returns:
            list : The history
        """
        return self._config.meta.history
