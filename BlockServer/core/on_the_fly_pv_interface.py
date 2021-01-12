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
from abc import ABCMeta, abstractmethod


class OnTheFlyPvInterface:
    """ This is an abstract base class to ensure that any class that needs to handle on-the-fly PVs
    implements all the correct methods.
    """
    __metaclass__ = ABCMeta

    def __init__(self):
        self.pvs_to_read = []
        self.pvs_to_write = []

    def read_pv_exists(self, pv):
        """ Checks whether the read PV is handled by this class.
        If the read PV is handled by a monitor then this MUST return False

        Args:
            pv (string): The PV name

        Returns:
            bool: Whether the PV exists for reading
        """
        return pv in self.pvs_to_read

    def write_pv_exists(self, pv):
        """ Checks whether the write PV is handled by this class.

        Args:
            pv (string): The PV name

        Returns:
            bool: Whether the PV exists for writing
        """
        return pv in self.pvs_to_write

    @abstractmethod
    def handle_pv_write(self, pv: str, data: str):
        """ Handles the request to write to the PV.

        Note: implementations of this method MUST run on a separate thread.

        Args:
            pv: The PV's name
            data: The value to write
        """
        pass

    @abstractmethod
    def handle_pv_read(self, pv):
        """ Handles the request to read the PV value

        Args:
            pv (string): The PV's name

        Returns:
            object: The value to return to the requesting client
        """
        pass

    @abstractmethod
    def update_monitors(self):
        """ Updates any monitors associated with the class.
        """
        pass

    @abstractmethod
    def on_config_change(self, full_init=False):
        """ Performs any tasks that need to be carried out on initialisation.

        For example: on loading a new configuration.

        Args:
            full_init (bool): Whether it is a full initialisation
        """
        pass
