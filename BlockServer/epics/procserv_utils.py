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
from server_common.channel_access import ChannelAccess
from server_common.utilities import print_and_log, ioc_restart_pending, retry


class ProcServWrapper:
    """A wrapper for accessing some of the functionality of ProcServ."""

    def __init__(self, prefix: str):
        """Constructor.
        Args:
            prefix (string): The prefix for the instrument
        """
        self.procserv_prefix = f"{prefix}CS:PS:"

    def start_ioc(self, ioc: str):
        """Starts the specified IOC.

        Args:
            ioc (string): The name of the IOC
        """
        print_and_log(f"Starting IOC {ioc}")
        ChannelAccess.caput(f"{self.procserv_prefix}{ioc}:START", 1)

    def stop_ioc(self, ioc: str):
        """Stops the specified IOC.

        Args:
            ioc (string): The name of the IOC
        """
        print_and_log(f"Stopping IOC {ioc}")
        ChannelAccess.caput(f"{self.procserv_prefix}{ioc}:STOP", 1, wait=True)

    def restart_ioc(self, ioc: str):
        """Restarts the specified IOC.

        Args:
            ioc (string): The name of the IOC
        """
        print_and_log(f"Restarting IOC {ioc}")
        ChannelAccess.caput(f"{self.procserv_prefix}{ioc}:RESTART", 1)

    def ioc_restart_pending(self, ioc: str):
        """Tests to see if an IOC restart is pending

        Args:
            ioc (string): The name of the IOC

        Returns:
            bool: Whether a restart is pending
        """
        return ioc_restart_pending(f"{self.procserv_prefix}{ioc}", ChannelAccess)

    def get_ioc_status(self, ioc: str):
        """Gets the status of the specified IOC.

        Args:
            ioc (string): The name of the IOC

        Returns:
            string : The status
        """
        pv_name = f"{self.procserv_prefix}{ioc}:STATUS"
        ans = ChannelAccess.caget(pv_name, as_string=True)
        if ans is None:
            raise Exception(f"Could not find IOC {ioc} (using pv {pv_name})")
        return ans.upper()

    def toggle_autorestart(self, ioc: str):
        """Toggles the auto-restart property.

        Args:
            ioc (string): The name of the IOC
        """
        # Check IOC is running, otherwise command is ignored
        print_and_log(f"Toggling auto-restart for IOC {ioc}")
        ChannelAccess.caput(f"{self.procserv_prefix}{ioc}:TOGGLE", 1)

    @retry(50, 0.1, ValueError)  # Retry for 5 seconds to get a valid value on failure
    def get_autorestart(self, ioc: str):
        """Gets the current auto-restart setting of the specified IOC.

        Args:
            ioc (string): The name of the IOC

        Returns:
            bool : Whether auto-restart is enabled
        """
        ioc_prefix = self.procserv_prefix + ioc

        ans = ChannelAccess.caget(f"{ioc_prefix}:AUTORESTART", as_string=True)
        if ans not in ["On", "Off"]:
            raise ValueError(f"Could not get auto-restart property for IOC {ioc_prefix}, got '{ans}'")

        return ans == "On"
