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
from typing import List, Union, Dict


class MetaData:
    """Represents the metadata from a configuration/component.

    Attributes:
        name (string): The name of the configuration
        pv (string): The PV for the configuration
        description (string): The description
        synoptic (string): The default synoptic view for this configuration
        history (list): The save history of the configuration
    """
    def __init__(self, config_name: str, pv_name: str = "", description: str = "", synoptic: str = ""):
        """ Constructor.

        Args:
            config_name: The name of the configuration
            pv: The PV for the configuration
            description: The description
            synoptic: The default synoptic view for this configuration
        """
        self.name = config_name
        self.pv = pv_name
        self.description = description
        self.synoptic = synoptic
        self.history = []
        self.isProtected = False
        self.configuresBlockGWAndArchiver = False

    def to_dict(self) -> Dict[str, Union[str, bool, List]]:
        """ Puts the metadata into a dictionary.

        Returns:
            The metadata
        """
        return {'name': self.name, 'pv': self.pv, 'description': self.description, 'synoptic': self.synoptic,
                'history': self.history, 'isProtected': self.isProtected,
                "configuresBlockGWAndArchiver": self.configuresBlockGWAndArchiver}
