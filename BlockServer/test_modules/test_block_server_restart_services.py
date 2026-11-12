# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2026 Science & Technology Facilities Council.
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

import unittest


@unittest.skip("Not yet implemented")
class TestBlockServerRestartServiceIoc(unittest.TestCase):
    def test_WHEN_restart_service_ioc_pv_written_THEN_restart_queued_with_iocs(self):
        """Writing a list like ["DBSVR"] queues restart_service_ioc with that list."""

    def test_GIVEN_manager_mode_WHEN_blocksvr_restarted_THEN_blockserver_restarts(self):
        """"BLOCKSVR" calls self._restart()."""

    def test_GIVEN_manager_mode_WHEN_gwblock_restarted_THEN_gateway_reloaded(self):
        """"GWBLOCK" calls self._gateway.reload()."""

    def test_GIVEN_manager_mode_WHEN_dbsvr_restarted_THEN_database_server_restart_pv_written(
        self,
    ):
        """"DBSVR" caputs 1 to CONTROL_SYSTEM_PREFIX + DatabasePVNames.RESTART."""

    def test_GIVEN_manager_mode_WHEN_other_service_ioc_restarted_THEN_restarted_via_ioc_control(
        self,
    ):
        """e.g. "INSTETC" calls ioc_control.restart_ioc("INSTETC", force=True)."""

    def test_GIVEN_ioc_not_in_service_list_WHEN_restarted_THEN_nothing_restarted(self):
        """A normal IOC is ignored: no restart, reload or caput."""

    def test_GIVEN_not_manager_mode_WHEN_service_ioc_restarted_THEN_nothing_restarted(self):
        """ManagerModeRequiredError is raised and no restart happens."""


if __name__ == "__main__":
    unittest.main()
