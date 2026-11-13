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
from unittest.mock import patch

from ibex_non_ca_helpers.compress_hex import compress_and_hex
from server_common.channel_access import ManagerModeRequiredError
from server_common.helpers import CONTROL_SYSTEM_PREFIX
from server_common.mocks.mock_ca_server import MockCAServer
from server_common.pv_names import BlockserverPVNames, DatabasePVNames

from block_server import BlockServer


class TestBlockServerRestartServiceIoc(unittest.TestCase):
    def setUp(self):
        self.block_server = BlockServer(MockCAServer(), test_mode=True)

        gateway_patcher = patch.object(self.block_server, "_gateway", create=True)
        self.mock_gateway = gateway_patcher.start()
        self.addCleanup(gateway_patcher.stop)

        ioc_control_patcher = patch.object(
            self.block_server, "_ioc_control", create=True
        )
        self.mock_ioc_control = ioc_control_patcher.start()
        self.addCleanup(ioc_control_patcher.stop)

        verify_patcher = patch("block_server.verify_manager_mode")
        self.mock_verify_manager_mode = verify_patcher.start()
        self.addCleanup(verify_patcher.stop)

        ca_patcher = patch("block_server.ChannelAccess")
        self.mock_channel_access = ca_patcher.start()
        self.addCleanup(ca_patcher.stop)

        exit_patcher = patch("block_server.os._exit")
        self.mock_exit = exit_patcher.start()
        self.addCleanup(exit_patcher.stop)

    def test_WHEN_restart_service_ioc_pv_written_THEN_restart_queued_with_iocs(self):
        value = compress_and_hex('["DBSVR"]').decode("utf-8")

        status = self.block_server.write(BlockserverPVNames.RESTART_SERVICE_IOC, value)

        self.assertTrue(status)
        self.assertEqual(
            self.block_server.write_queue.get_nowait(),
            (
                self.block_server.restart_service_ioc,
                (["DBSVR"], True),
                "RESTART_SERVICE_IOC",
            ),
        )

    def test_GIVEN_manager_mode_WHEN_blocksvr_restarted_THEN_blockserver_restarts(self):
        self.block_server.restart_service_ioc(["BLOCKSVR"])

        self.mock_verify_manager_mode.assert_called_once()
        self.mock_exit.assert_called_once_with(0)

    def test_GIVEN_manager_mode_WHEN_gwblock_restarted_THEN_gateway_reloaded(self):
        self.block_server.restart_service_ioc(["GWBLOCK"])

        self.mock_verify_manager_mode.assert_called_once()
        self.mock_gateway.reload.assert_called_once()

    def test_GIVEN_manager_mode_WHEN_dbsvr_restarted_THEN_database_server_restart_pv_written(
        self,
    ):
        self.block_server.restart_service_ioc(["DBSVR"])

        self.mock_verify_manager_mode.assert_called_once()
        self.mock_channel_access.caput.assert_called_once_with(
            CONTROL_SYSTEM_PREFIX + DatabasePVNames.RESTART, 1
        )

    def test_GIVEN_manager_mode_WHEN_other_service_ioc_restarted_THEN_restarted_via_ioc_control(
        self,
    ):
        self.block_server.restart_service_ioc(["INSTETC"])

        self.mock_verify_manager_mode.assert_called_once()
        self.mock_ioc_control.restart_ioc.assert_called_once_with("INSTETC", force=True)

    def test_GIVEN_ioc_not_in_service_list_WHEN_restarted_THEN_nothing_restarted(self):
        self.block_server.restart_service_ioc(["SIMPLE"])

        self.mock_verify_manager_mode.assert_not_called()
        self.mock_exit.assert_not_called()
        self.mock_channel_access.caput.assert_not_called()
        self.mock_gateway.reload.assert_not_called()
        self.mock_ioc_control.restart_ioc.assert_not_called()

    def test_GIVEN_not_manager_mode_WHEN_service_ioc_restarted_THEN_nothing_restarted(
        self,
    ):
        self.mock_verify_manager_mode.side_effect = ManagerModeRequiredError(
            "not manager"
        )

        with self.assertRaises(ManagerModeRequiredError):
            self.block_server.restart_service_ioc(["INSTETC"])

        self.mock_ioc_control.restart_ioc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
