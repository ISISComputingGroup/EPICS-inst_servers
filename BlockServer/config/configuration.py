# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2025 Science & Technology Facilities Council.
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

"""Contains all the code for defining a configuration or component"""

from collections import OrderedDict
from typing import Dict

from BlockServer.config.block import Block
from BlockServer.config.globalmacros import Globalmacro
from BlockServer.config.group import Group
from BlockServer.config.ioc import IOC
from BlockServer.config.metadata import MetaData
from BlockServer.core.constants import GRP_NONE
from server_common.helpers import PVPREFIX_MACRO
from server_common.utilities import print_and_log


class Configuration:
    """The Configuration class.

    Attributes:
        blocks (OrderedDict): The blocks for the configuration
        macros (dict): The EPICS/BlockServer related macros
        groups (OrderedDict): The groups for the configuration
        iocs (OrderedDict): The IOCs for the configuration
        meta (MetaData): The meta-data for the configuration
        components (OrderedDict): The components which are part of the configuration
        is_component (bool): Whether it is actually a component
        globalmacros (OrderedDict): The globalmacros for the configuration
    """

    def __init__(self, macros: Dict):
        """Constructor.

        Args:
            macros: The dictionary containing the macros
        """
        # All dictionary keys are lowercase except iocs which is uppercase
        self.blocks = OrderedDict()
        self.macros = macros
        self.groups = OrderedDict()
        self.iocs = OrderedDict()
        self.meta = MetaData("")
        self.components = OrderedDict()
        self.is_component = False
        self.globalmacros = OrderedDict()

    def add_block(self, name: str, pv: str, group: str = GRP_NONE, local: bool = True, **kwargs):
        """Add a block to the configuration.

        Args:
            name: The name for the new block
            pv: The PV that is aliased
            group: The group that the block belongs to
            local: Is the block local
            kwargs: Keyword arguments for the other parameters
        """
        # Check block name is unique
        if name.lower() in self.blocks.keys():
            raise ValueError("Failed to add block as name is not unique")

        if local:
            # Strip off the MYPVPREFIX in the PV name (not the block name!)
            pv = pv.replace(self.macros[PVPREFIX_MACRO], "")

        self.blocks[name.lower()] = Block(name, pv, local, **kwargs)

        if group is not None:
            # If group does not exists then add it
            if group.lower() not in self.groups.keys():
                self.groups[group.lower()] = Group(group)
            self.groups[group.lower()].blocks.append(name)

    def add_ioc(
        self,
        name: str,
        component: str = None,
        autostart: bool = None,
        restart: bool = None,
        macros: Dict = None,
        pvs: Dict = None,
        pvsets: Dict = None,
        simlevel: str = None,
        remotePvPrefix: str = None,
    ):
        """Add an IOC to the configuration.

        Args:
            name (string): The name of the IOC to add
            component: The component that the IOC belongs to
            autostart: Should the IOC automatically start
            restart: Should the IOC automatically restart
            macros: The macro sets relating to the IOC
            pvs:
            pvsets: Any PV values that should be set at start up
            simlevel: Sets the simulation level
            remotePvPrefix: Sets the remote PV prefix to use for this IOC

        """
        # Only add it if it has not been added before
        if name.upper() in self.iocs.keys():
            print_and_log(
                f"Warning: IOC '{name}' is already part of the configuration. Not adding it again."
            )
        else:
            self.iocs[name.upper()] = IOC(
                name, autostart, restart, component, macros, pvs, pvsets, simlevel, remotePvPrefix
            )

    def get_name(self) -> str:
        """Gets the name of the configuration.

        Returns:
            The name of this configuration
        """
        return (
            self.meta.name.decode("utf-8") if isinstance(self.meta.name, bytes) else self.meta.name
        )

    def set_name(self, name: str):
        """Sets the configuration's name.

        Args:
            name: The new name for the configuration
        """
        self.meta.name = name

    def add_globalmacro(
        self,
        name: str,
        macros: Dict) -> None:
        """Add an IOC with its global macros to the configuration.

        Args:
            name (string): The name of the IOC to add
            macros: The macro sets relating to the IOC

        """
        # Only add it if it has not been added before
        if name.upper() in self.globalmacros.keys():
            print_and_log(
                f"Warning: IOC '{name}' is already part of the configuration. Not adding it again."
            )
        else:
            self.globalmacros[name.upper()] = Globalmacro(name, macros)
