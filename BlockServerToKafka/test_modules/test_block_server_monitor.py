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

import unittest

from mock import MagicMock, patch

from BlockServerToKafka.block_server_monitor import BlockServerMonitor


@patch("CaChannel.CaChannel")
class TestBlockServerMonitor(unittest.TestCase):
    test_address = "TEST_ADDRESS"
    test_prefix = "TEST_PREFIX"

    def setUp(self):
        self.mock_producer = MagicMock()
        self.bs_monitor = BlockServerMonitor(
            self.test_address, self.test_prefix, self.mock_producer
        )

    def test_WHEN_convert_one_char_to_string_THEN_returns_character(
        self,
        mock_ca_channel,
    ):
        c = "a"
        arr = [ord(c)]
        self.assertEqual(c, self.bs_monitor.convert_to_string(bytearray(arr)))

    def test_WHEN_convert_many_chars_to_string_THEN_returns_characters(self, mock_ca_channel):
        chars = "hello world"
        arr = [ord(c) for c in chars]
        self.assertEqual(chars, self.bs_monitor.convert_to_string(bytearray(arr)))

    def test_WHEN_convert_chars_with_null_at_end_THEN_nulls_removed(
        self,
        mock_ca_channel,
    ):
        chars = "hello world"
        arr = [ord(c) for c in chars]
        for i in range(3):
            arr.append(0)
        self.assertEqual(chars, self.bs_monitor.convert_to_string(bytearray(arr)))

    def test_WHEN_convert_chars_with_null_at_start_THEN_nulls_removed(
        self,
        mock_ca_channel,
    ):
        chars = "hello world"
        arr = [ord(c) for c in chars]
        for i in range(3):
            arr.insert(0, 0)
        self.assertEqual(chars, self.bs_monitor.convert_to_string(bytearray(arr)))

    def test_WHEN_convert_chars_with_nulls_in_centre_THEN_nulls_removed(self, mock_ca_channel):
        chars = "hello world"
        arr = [ord(c) for c in chars]
        arr.insert(4, 0)
        self.assertEqual(chars, self.bs_monitor.convert_to_string(bytearray(arr)))

    def test_WHEN_convert_nulls_THEN_empty_string_returned(
        self,
        mock_ca_channel,
    ):
        arr = [0] * 10
        self.assertEqual("", self.bs_monitor.convert_to_string(bytearray(arr)))

    def test_GIVEN_no_previous_pvs_WHEN_update_config_called_THEN_producer_is_called(
        self, mock_ca_channel
    ):
        self.bs_monitor.update_config(["BLOCK"])
        self.mock_producer.add_config.assert_called_once()

    def test_GIVEN_no_previous_pvs_WHEN_update_config_called_THEN_producer_is_called_containing_block_name(
        self, mock_ca_channel
    ):
        block = "BLOCK"
        self.bs_monitor.update_config([block])
        self.mock_producer.add_config.assert_called_with(
            [self.bs_monitor.block_name_to_pv_name(block)]
        )

    def test_GIVEN_previous_pvs_WHEN_update_config_called_with_same_pvs_THEN_producer_is_not_called(
        self, mock_ca_channel
    ):
        block = "BLOCK"
        self.bs_monitor.update_config([block])
        self.bs_monitor.update_config([block])
        self.mock_producer.add_config.assert_called_once()

    def test_GIVEN_previous_pvs_WHEN_update_config_called_with_different_pvs_THEN_producer_is_called(
        self, mock_ca_channel
    ):
        self.bs_monitor.update_config(["OLD_BLOCK"])
        self.mock_producer.reset_mock()
        self.bs_monitor.update_config(["NEW_BLOCK"])
        self.mock_producer.add_config.assert_called_once()
