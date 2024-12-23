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

from streaming_data_types.fbschemas.forwarder_config_update_fc00.Protocol import (
    Protocol,
)
from streaming_data_types.fbschemas.forwarder_config_update_fc00.UpdateType import (
    UpdateType,
)
from streaming_data_types.forwarder_config_update_fc00 import deserialise_fc00

from BlockServerToKafka.forwarder_config import ForwarderConfig


class TestForwarderConfig(unittest.TestCase):
    test_schema = "schema"
    test_topic = "topic"
    test_block_1 = "block1"
    test_block_2 = "block2"

    @staticmethod
    def is_flatbuffers(payload):
        try:
            deserialise_fc00(payload)
        except ValueError:
            return False
        return True

    def setUp(self):
        self.kafka_forwarder = ForwarderConfig(self.test_topic, schema=self.test_schema)
        self.config_with_one_block = [self.test_block_1]
        self.config_with_two_blocks = [self.test_block_1, self.test_block_2]

    def test_WHEN_new_forwarder_config_created_THEN_returns_valid_flatbuffers(self):
        output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        self.assertTrue(self.is_flatbuffers(output))

    def test_WHEN_new_forwarder_config_created_THEN_returns_configuration_update_containing_add_command(
        self,
    ):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = deserialise_fc00(raw_output)
        self.assertEqual(output.config_change, UpdateType.ADD)

    def test_WHEN_forwarder_config_removed_THEN_output_has_correct_command_type(self):
        raw_output = self.kafka_forwarder.remove_forwarder_configuration(self.config_with_one_block)
        output = deserialise_fc00(raw_output)
        self.assertEqual(output.config_change, UpdateType.REMOVE)

    def test_WHEN_all_pvs_removed_THEN_output_has_correct_command_type(self):
        raw_output = self.kafka_forwarder.remove_all_forwarder_configuration()
        output = deserialise_fc00(raw_output)
        self.assertEqual(output.config_change, UpdateType.REMOVEALL)

    def test_WHEN_new_forwarder_config_created_THEN_returns_flatbuffer_containing_streams_with_channels_and_converters(
        self,
    ):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = deserialise_fc00(raw_output)
        self.assertNotEqual(0, len(output[1]))
        for stream in output[1]:
            self.assertEqual(self.test_block_1, stream.channel)
            self.assertEqual(self.test_topic, stream.topic)
            self.assertEqual(Protocol.CA, stream.protocol)

    def test_GIVEN_using_version_4_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_streams_with_pva_channel_type(
        self,
    ):
        kafka_version_4 = ForwarderConfig(
            epics_protocol=Protocol.PVA,  # pyright: ignore noqa
            topic=self.test_topic,
        )
        raw_output = kafka_version_4.create_forwarder_configuration(self.config_with_one_block)
        output = deserialise_fc00(raw_output)
        self.assertNotEqual(0, len(output[1]))
        for stream in output[1]:
            self.assertEqual(stream.protocol, Protocol.PVA)

    def test_GIVEN_configuration_with_one_block_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_one_stream(
        self,
    ):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = deserialise_fc00(raw_output)
        self.assertEqual(1, len(output[1]))

    def test_GIVEN_configuration_with_two_block_WHEN_new_forwarder_config_created_THEN_returns_JSON_containing_two_stream(
        self,
    ):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(
            self.config_with_two_blocks
        )
        output = deserialise_fc00(raw_output)
        self.assertEqual(2, len(output[1]))

    def test_GIVEN_configuration_with_one_block_WHEN_new_forwarder_config_created_THEN_returns_block_pv_string(
        self,
    ):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(self.config_with_one_block)
        output = deserialise_fc00(raw_output)
        stream = output[1][0]
        self.assertEqual(self.test_block_1, stream.channel)

    def test_GIVEN_configuration_with_two_blocks_WHEN_new_forwarder_config_created_THEN_returns_both_block_pv_string(
        self,
    ):
        raw_output = self.kafka_forwarder.create_forwarder_configuration(
            self.config_with_two_blocks
        )
        output = deserialise_fc00(raw_output)
        for blk in [self.test_block_1, self.test_block_2]:
            self.assertTrue(blk in [stream.channel for stream in output[1]])

    def test_WHEN_removed_old_forwarder_THEN_JSON_returns_valid(self):
        output = self.kafka_forwarder.remove_forwarder_configuration(self.config_with_one_block)
        self.assertTrue(self.is_flatbuffers(output))

    def test_GIVEN_configuration_with_one_block_WHEN_removed_old_forwarder_THEN_returns_JSON_containing_block_pv_string(
        self,
    ):
        raw_output = self.kafka_forwarder.remove_forwarder_configuration(self.config_with_one_block)
        output = deserialise_fc00(raw_output)
        self.assertEqual(self.test_block_1, output[1][0].channel)

    def test_GIVEN_configuration_with_two_blocks_WHEN_removed_old_forwarder_THEN_returns_JSON_containing_both_block_pv_string(
        self,
    ):
        raw_output = self.kafka_forwarder.remove_forwarder_configuration(
            self.config_with_two_blocks
        )
        output = deserialise_fc00(raw_output)
        for blk in [self.test_block_1, self.test_block_2]:
            self.assertTrue(blk in [stream.channel for stream in output[1]])
