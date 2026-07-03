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
from typing import Dict, List, Union


class Group:
    """Represents a group.

    Attributes:
        name (string): The name of the group
        blocks (dict): The blocks that are in the group
        component (string): The component the group belongs to
    """

    def __init__(self, name: str, component: str | None = None) -> None:
        """Constructor.

        Args:
            name: The name for the group
            component: The component to which the group belongs
        """
        self.name = name
        self.blocks = []
        self.component = component

    def __str__(self) -> str:
        return f"Name: {self.name}, COMPONENT: {self.component}, Blocks: {self.blocks}"

    def to_dict(self) -> Dict[str, Union[str, List, None]]:
        """Puts the group's details into a dictionary.

        Returns:
            The group's details
        """
        return {"name": self.name, "blocks": self.blocks, "component": self.component}
