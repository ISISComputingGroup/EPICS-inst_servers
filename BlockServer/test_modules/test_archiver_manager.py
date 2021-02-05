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
import os

# Set MYPVPREFIX env var
from hamcrest import *
from mock import patch, mock_open

from ArchiverAccess.test_modules.stubs import FileStub
from BlockServer.config.block import Block

os.environ['MYPVPREFIX'] = ""

from BlockServer.epics.archiver_manager import ArchiverManager
import unittest


HEADER_XML= """<?xml version="1.0" ?>
<engineconfig>
\t<group>
\t\t<name>BLOCKS</name>
"""

BLOCKS_TO_DATAWEB_XML="""\t</group>
\t<group>
\t\t<name>DATAWEB</name>
"""

FOOTER_XML="""\t</group>
</engineconfig>
"""

SCAN_BLOCK="""\t\t<channel>
\t\t\t<name>{prefix}{block_name}</name>
\t\t\t<period>0:{period_min:02}:{period_s:02}</period>
\t\t\t<scan/>
\t\t</channel>
"""

MONITOR_BLOCK="""\t\t<channel>
\t\t\t<name>{prefix}{block_name}</name>
\t\t\t<period>0:00:01</period>
\t\t\t<monitor>{deadband}</monitor>
\t\t</channel>
"""


class TestArchiveManager(unittest.TestCase):
    def setUp(self):
        self._setting_path = "blockserver_xml_path"
        self.archiver_manager = ArchiverManager(uploader_path=None, settings_path=self._setting_path)
        self.config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "settings")

    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_no_blocks_WHEN_update_THEN_xml_for_archiver_contains_just_header(self, mock_file):
        blocks = []
        prefix = "prefix"
        expected_output = "{}{}{}".format(HEADER_XML, BLOCKS_TO_DATAWEB_XML, FOOTER_XML).splitlines()

        self.archiver_manager.update_archiver(prefix, blocks, False, self.config_dir)

        assert_that(mock_file.file_contents[self._setting_path], contains_exactly(*expected_output))

    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_one_blocks_is_not_logged_WHEN_update_THEN_xml_for_archiver_contains_block_in_dataweb_group(self, mock_file):
        expected_name="block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name, period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks, False, self.config_dir)

        assert_that(mock_file.file_contents[self._setting_path], has_items(*block_str.splitlines()))

    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_one_blocks_is_logged_periodic_WHEN_update_THEN_xml_for_archiver_contains_periodic_block(self, mock_file):
        expected_name="block"
        expected_pv = "pv"
        expecter_logging_rate_s = 30
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=expecter_logging_rate_s, log_deadband=1)]
        prefix = "prefix"
        block_str = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name, period_s=expecter_logging_rate_s, period_min=0)

        self.archiver_manager.update_archiver(prefix, blocks, False, self.config_dir)

        assert_that(mock_file.file_contents[self._setting_path], has_items(*block_str.splitlines()))

    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_one_blocks_is_not_periodic_WHEN_update_THEN_xml_for_archiver_contains_periodic_block(self, mock_file):
        expected_name="block"
        expected_pv = "pv"
        expected_deadband = 30
        blocks = [Block(expected_name, expected_pv, log_periodic=False, log_rate=1, log_deadband=expected_deadband)]
        prefix = "prefix"
        block_str = MONITOR_BLOCK.format(prefix=prefix, block_name=expected_name, deadband=expected_deadband)

        self.archiver_manager.update_archiver(prefix, blocks, False, self.config_dir)

        assert_that(mock_file.file_contents[self._setting_path], has_items(*block_str.splitlines()))

    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_one_blocks_WHEN_update_THEN_xml_for_archiver_contains_runcontrl_low_value_block_in_dataweb_group(self, mock_file):
        expected_name = "block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":RC:LOW.VAL", period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks, False, self.config_dir)

        assert_that(mock_file.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))

    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_one_blocks_WHEN_update_THEN_xml_for_archiver_contains_runcontrl_high_value_block_in_dataweb_group(self, mock_file):
        expected_name = "block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":RC:HIGH.VAL", period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks, False, self.config_dir)

        assert_that(mock_file.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))

    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_one_blocks_WHEN_update_THEN_xml_for_archiver_contains_runcontrl_inrange_block_in_dataweb_group(self, mock_file):
        expected_name = "block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":RC:INRANGE.VAL", period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks, False, self.config_dir)

        assert_that(mock_file.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))

    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_one_blocks_WHEN_update_THEN_xml_for_archiver_contains_runcontrl_enabled_block_in_dataweb_group(self, mock_file):
        expected_name = "block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":RC:ENABLE.VAL", period_s=0, period_min=5)

        self.archiver_manager.update_archiver(prefix, blocks, False, self.config_dir)

        assert_that(mock_file.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))

    @patch('BlockServer.epics.archiver_manager.copyfile')
    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_that_configuration_contains_archiver_xml_THEN_xml_for_archiver_uses_that_file(self, mock_file, copyfile_mock):
        mock_file.clear()
        expected_name = "block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        config_dir = os.path.join(self.config_dir, "non_empty")

        self.archiver_manager.update_archiver(prefix, blocks, True, config_dir)

        copyfile_mock.assert_called_once_with(os.path.join(config_dir, "block_config.xml"), self._setting_path)
        assert_that(mock_file.file_contents, empty())

    @patch('BlockServer.epics.archiver_manager.copyfile')
    @patch('builtins.open', new_callable=mock_open, mock=FileStub)
    def test_GIVEN_that_configuration_claims_but_does_not_contain_archiver_xml_THEN_xml_for_archiver_generates(
            self, mock_file, copyfile_mock):
        mock_file.clear()
        expected_name = "block"
        expected_pv = "pv"
        blocks = [Block(expected_name, expected_pv, log_periodic=True, log_rate=0, log_deadband=1)]
        prefix = "prefix"
        block_str_rc_low = SCAN_BLOCK.format(prefix=prefix, block_name=expected_name + ":RC:ENABLE.VAL", period_s=0,
                                             period_min=5)

        config_dir = os.path.join(self.config_dir, "empty")

        self.archiver_manager.update_archiver(prefix, blocks, True, config_dir)

        copyfile_mock.assert_not_called()
        assert_that(mock_file.file_contents[self._setting_path], has_items(*block_str_rc_low.splitlines()))
