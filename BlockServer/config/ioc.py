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

import copy
from typing import Any, Dict, List, Union


class IOC:
    """Represents an IOC.

    Attributes:
        name (string): The name of the IOC
        autostart (bool): Whether the IOC should automatically
            start/restart when the configuration is loaded/changed
        restart (bool): If auto start is true, then proc serv will
            restart the IOC if it terminates unexpectedly
        component (string): The component the IOC belongs to
        macros (dict): The IOC's macros
        pvs (dict): The IOC's PVs
        pvsets (dict): The IOC's PV sets
        simlevel (string): The level of simulation
    """

    def __init__(
        self,
        name: str,
        autostart: bool = True,
        restart: bool = True,
        component: str = None,
        macros: Dict = None,
        pvs: Dict = None,
        pvsets: Dict = None,
        simlevel: str = None,
        remote_pv_prefix: str = None,
    ) -> None:
        """Constructor.

        Args:
            name: The name of the IOC
            autostart: Whether the IOC should automatically
                start/restart when the configuration is
            loaded/changed
            restart: If auto start is true, then proc serv will
                restart the IOC if it terminates unexpectedly
            component: The component the IOC belongs to
            macros: The IOC's macros
            pvs: The IOC's PVs
            pvsets: The IOC's PV sets
            simlevel: The level of simulation
            remote_pv_prefix: The remote pv prefix
        """
        self.name = name
        self.autostart = autostart
        self.restart = restart
        self.component = component
        self.remote_pv_prefix = remote_pv_prefix

        if simlevel is None:
            self.simlevel = "none"
        else:
            self.simlevel = simlevel.lower()

        self.macros = {}
        if macros is not None:
            # Remove macros that are set to use default, they can be gotten from config.xml
            # so there is no need for them to be stored in the config.
            for name, data in macros.items():
                if not ("useDefault" in data and data["useDefault"]):
                    self.macros.update({name: data})
                    self.macros[name].pop("useDefault")

        if pvs is None:
            self.pvs = {}
        else:
            self.pvs = pvs

        if pvsets is None:
            self.pvsets = {}
        else:
            self.pvsets = pvsets

    @staticmethod
    def _dict_to_list(in_dict: Dict[str, Any]) -> List[Any]:
        """Converts into a format better for the GUI to parse, namely a list.

        It's messy but it's what the GUI wants.

        Args:
            in_dict: The dictionary to be converted

        Returns:
            The newly created list
        """
        out_list = []
        for k, v in in_dict.items():
            # Take a copy as we do not want to modify the original
            c = copy.deepcopy(v)
            c["name"] = k
            out_list.append(c)
        return out_list

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, component={self.component})"

    def to_dict(self) -> Dict[str, Union[str, bool, List[Any]]]:
        """Puts the IOC's details into a dictionary.

        Returns:
            The IOC's details
        """
        return {
            "name": self.name,
            "autostart": self.autostart,
            "restart": self.restart,
            "simlevel": self.simlevel,
            "pvs": self._dict_to_list(self.pvs),
            "pvsets": self._dict_to_list(self.pvsets),
            "macros": self._dict_to_list(self.macros),
            "component": self.component,
            "remotePvPrefix": self.remote_pv_prefix,
        }

    def get(self, name: str) -> bool | str | Dict | None:
        return self.__getattribute__(name)

    def __getitem__(self, name: str) -> bool | str | Dict | None:
        return self.__getattribute__(name)
