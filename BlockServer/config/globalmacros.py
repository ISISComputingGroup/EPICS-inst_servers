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

import copy
from typing import Any, Dict, List


class Globalmacro:
    """Represents an IOC with its global macros.

    Attributes:
        name (string): The name of the IOC
        macros (dict): The IOC's macros
    """

    def __init__(
        self,
        name: str,
        macros: Dict[str, str],
    ) -> None:
        """Constructor.

        Args:
            name: The name of the IOC
            macros: The IOC's macros
        """
        self.name = name

        if macros is None:
            self.macros = {}
        else:
            self.macros = macros

    @staticmethod
    def _dict_to_list(in_dict: Dict[str, Any]) -> List[Any]:
        """Converts into a format better for the GUI to parse, namely a list.

        Args:
            in_dict: The dictionary to be converted

        Returns:
            The newly created list
        """
        out_list = []
        if in_dict:
            for k, v in in_dict.items():
                # Take a copy as we do not want to modify the original
                c = copy.deepcopy(v)
                c["name"] = k
                out_list.append(c)
        return out_list

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"

    def to_dict(self) -> Dict[str, str | Dict[str, str]]:
        """Puts the IOC-globalmacro's details into a dictionary.

        Returns:
            The IOC-Global Macros' details
        """
        return {
            "name": self.name,
            "macros": self.macros,
        }

    def get(self, name: str) -> None:
        return self.__getattribute__(name)

    def __getitem__(self, name: str) -> None:
        return self.__getattribute__(name)


class GlobalmacroHelper:
    """Converts global macro data to Globalmacro Object.

    Consists of static methods only.
    """

    @staticmethod
    def row_to_globalmacro(globalmacros: Dict, row: str) -> None:
        """converts a row from the globals file to globalmacro data.

        Args:
            globalmacros: The current list of global macros
            row: The IOC's (or All IOCs) global macro record
        """
        ioc_separator = "__"
        equal_to = "="
        all_iocs = ioc_separator
        # Each record is of the form IOC__MACRO=VALUE
        # Where there is no __ the Macro is applicable for all IOCs
        if equal_to in row:
            ioc_macro, value = row.rsplit(equal_to, maxsplit=1)
            to_add_ioc = {}
            if ioc_separator in ioc_macro:
                ioc, macro = ioc_macro.split(ioc_separator, maxsplit=1)
            else:
                ioc = all_iocs
                macro = ioc_macro

            if ioc in globalmacros:
                to_add_ioc = globalmacros[ioc]
            to_add_ioc[macro] = value.strip()
            globalmacros[ioc] = to_add_ioc
