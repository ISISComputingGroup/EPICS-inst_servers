from __future__ import absolute_import, division, print_function, unicode_literals

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


class MockProcServWrapper(object):
    """
    Mock ProcServer
    """

    def __init__(self) -> None:
        self.ps_status = dict()
        self.ps_status["simple1"] = "SHUTDOWN"
        self.ps_status["simple2"] = "SHUTDOWN"
        self.ps_status["testioc"] = "SHUTDOWN"
        self.ps_status["stopdioc"] = "SHUTDOWN"

    @staticmethod
    def generate_prefix(prefix: str, ioc: str) -> str:
        return f"{prefix}CS:PS:{ioc}"

    def start_ioc(self, prefix: str, ioc: str) -> None:
        self.ps_status[ioc.lower()] = "RUNNING"

    def stop_ioc(self, prefix: str, ioc: str) -> None:
        """Stops the specified IOC"""
        self.ps_status[ioc.lower()] = "SHUTDOWN"

    def restart_ioc(self, prefix: str, ioc: str) -> None:
        self.ps_status[ioc.lower()] = "RUNNING"

    def get_ioc_status(self, prefix: str, ioc: str) -> str:
        if ioc.lower() not in self.ps_status.keys():
            raise TimeoutError("Could not find IOC (%s)" % self.generate_prefix(prefix, ioc))
        else:
            return self.ps_status[ioc.lower()]

    def ioc_exists(self, prefix: str, ioc: str) -> bool:
        try:
            self.get_ioc_status(prefix, ioc)
            return True
        except TimeoutError:
            return False
