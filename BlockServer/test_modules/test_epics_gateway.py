# This file is part of the ISIS IBEX application.
# Copyright (C) 2012-2020 Science & Technology Facilities Council.
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

import os
import unittest

from hamcrest import *
from mock import MagicMock, mock_open, patch

from ArchiverAccess.test_modules.stubs import FileStub
from BlockServer.config.block import Block
from BlockServer.epics.gateway import ALIAS_HEADER, Gateway


class TestEpicsGateway(unittest.TestCase):

    def setUp(self):
        self.gateway_prefix = "GATEWAY:"
        self.gateway_file_path = "FILE_PATH"
        self.prefix = "INST:"
        self.block_prefix = self.prefix + "BLOCK:"
        self.control_sys_prefix = self.prefix + "CONTROL:"
        self.config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "settings")

        self.gateway = Gateway(self.gateway_prefix, self.prefix, self.gateway_file_path, self.block_prefix,
                               self.control_sys_prefix)

    @patch("BlockServer.epics.gateway.ChannelAccess")
    def test_GIVEN_gateway_pv_doesnt_exist_WHEN_exist_called_THEN_returns_false(self, channel_access):
        channel_access.caget = MagicMock(return_value=None)
        self.assertFalse(self.gateway.exists())
        channel_access.caget.assert_called_with(self.gateway_prefix + "pvtotal")

    @patch("BlockServer.epics.gateway.ChannelAccess")
    def test_GIVEN_gateway_pv_exists_WHEN_exist_called_THEN_returns_true(self, channel_access):
        channel_access.caget = MagicMock(return_value="Hi")
        self.assertTrue(self.gateway.exists())
        channel_access.caget.assert_called_with(self.gateway_prefix + "pvtotal")

    def _assert_lines_correct(self, actual_lines, expected_lines):
        sanitised_lines = list()
        for line in actual_lines:
            if not line.startswith("##") and line != "":
                sanitised_lines.append(line.split())

        self.assertListEqual(sanitised_lines, expected_lines)

    def test_GIVEN_local_PV_without_suffix_or_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV\\1"],
                          [alias, "ALIAS", "INST:MY_PV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_remote_PV_without_suffix_or_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "MY_PV\\1"],
                          [alias, "ALIAS", "MY_PV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_local_PV_with_suffix_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV.EGU"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV\\1"],
                          ["{}[.]VAL".format(alias), "ALIAS", "INST:MY_PV.EGU"],
                          [alias, "ALIAS", "INST:MY_PV.EGU"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_remote_PV_with_suffix_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV.RBV"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "MY_PV\\1"],
                          ["{}[.]VAL".format(alias), "ALIAS", "MY_PV.RBV"],
                          [alias, "ALIAS", "MY_PV.RBV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_local_PV_with_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV:SP"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\(:SP\)?\([.:].*\)".format(alias), "ALIAS", "INST:MY_PV:SP\\2"],
                          [r"{}\(:SP\)?".format(alias), "ALIAS", "INST:MY_PV:SP"]]

        lines = self.gateway.generate_alias(blockname, block_pv, True)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_remote_PV_with_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_PV:SP"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\(:SP\)?\([.:].*\)".format(alias), "ALIAS", "MY_PV:SP\\2"],
                          [r"{}\(:SP\)?".format(alias), "ALIAS", "MY_PV:SP"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_remote_PV_with_VAL_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "MY_BLOCK", "MY_TEST.VAL"
        alias = "INST:BLOCK:MY_BLOCK"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "MY_TEST\\1"],
                          ["{}".format(alias), "ALIAS", "MY_TEST"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    def test_GIVEN_local_lowercase_PV_without_suffix_or_SP_WHEN_alias_generated_THEN_lines_as_expected(self):
        blockname, block_pv = "My_Block", "MY_PV"
        alias = "INST:BLOCK:My_Block"
        expected_lines = [[r"{}\([.:].*\)".format(alias), "ALIAS", "MY_PV\\1"],
                          [alias, "ALIAS", "MY_PV"],
                          [r"{}\([.:].*\)".format(alias.upper()), "ALIAS", "MY_PV\\1"],
                          [alias.upper(), "ALIAS", "MY_PV"]]

        lines = self.gateway.generate_alias(blockname, block_pv, False)

        self._assert_lines_correct(lines, expected_lines)

    @patch('BlockServer.epics.gateway.copyfile')
    @patch('BlockServer.epics.gateway.Gateway._reload')
    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_configuration_has_pvlist_WHEN_set_new_aliases_THEN_pvlist_copied(self, mock_file,
                                                                                    reload_mock, copyfile_mock):
        mock_file.clear()
        config_dir = os.path.join(self.config_dir, "non_empty")
        expected_name = "block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]

        self.gateway.set_new_aliases(blocks, True, config_dir)

        copyfile_mock.assert_called_once_with(os.path.join(config_dir, "gwblock.pvlist"), self.gateway_file_path)
        assert_that(mock_file.file_contents, empty())

    @patch('BlockServer.epics.gateway.copyfile')
    @patch('BlockServer.epics.gateway.Gateway._reload')
    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_configuration_claims_has_pvlist_BUT_does_not_WHEN_set_new_aliases_THEN_pvlist_copied(
            self, mock_file, reload_mock, copyfile_mock):
        mock_file.clear()
        config_dir = os.path.join(self.config_dir, "empty")
        expected_name = "block"
        expected_pv = "pv"
        blocks = {expected_name: Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)}
        alias = "INST:BLOCK:block"
        expected_lines = [line.split() for line in ALIAS_HEADER.format("INST:").splitlines() if not line.startswith("##") and line != ""] + [
            [r"{}\([.:].*\)".format(alias), "ALIAS", "INST:{}\\1".format(expected_pv)],
            [alias, "ALIAS", "INST:" + expected_pv],
            [r"{}\([.:].*\)".format(alias.upper()), "ALIAS", "INST:{}\\1".format(expected_pv)],
            [alias.upper(), "ALIAS", "INST:" + expected_pv],
            ['INST:CS:GATEWAY:BLOCKSERVER:.*', 'ALLOW', 'ANYBODY', '1'],
            ['INST:CS:GATEWAY:BLOCKSERVER:report[1-9]Flag', 'ALLOW', 'ANYBODY', '1'],
            ['INST:CS:SB:[^:]*:[ADR]C:.*', 'DENY'],
            ['!INST:CS:\\(SB\\|GATEWAY\\):.*', 'DENY']
        ]

        self.gateway.set_new_aliases(blocks, True, config_dir)

        copyfile_mock.assert_not_called()
        print("Mocked File")
        for line in mock_file.file_contents[self.gateway_file_path]:
            print(line)
        print("----------------------------------")
        print("Expected Lines")
        for line in expected_lines:
            print(line)
        self._assert_lines_correct(mock_file.file_contents[self.gateway_file_path], expected_lines)
