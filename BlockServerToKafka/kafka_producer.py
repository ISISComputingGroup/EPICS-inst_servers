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
from time import sleep
from typing import List

from kafka import KafkaConsumer, KafkaProducer, errors
from streaming_data_types.fbschemas.forwarder_config_update_fc00.Protocol import (
    Protocol,
)

from BlockServerToKafka.forwarder_config import ForwarderConfig
from server_common.utilities import print_and_log


class ProducerWrapper:
    """
    A wrapper class for the kafka producer.
    """

    def __init__(
        self,
        server: str,
        config_topic: str,
        data_topic: str,
        epics_protocol: Protocol = Protocol.CA,
    ) -> None:
        self.topic = config_topic
        self.converter = ForwarderConfig(data_topic, epics_protocol)
        self._set_up_producer(server)

    def _set_up_producer(self, server: str) -> None:
        try:
            self.client = KafkaConsumer(bootstrap_servers=server)
            self.producer = KafkaProducer(bootstrap_servers=server)
            if not self.topic_exists(self.topic):
                print_and_log(
                    f"WARNING: topic {self.topic} does not exist. It will be created by default."
                )
        except errors.NoBrokersAvailable:
            print_and_log(f"No brokers found on server: {server[0]}")
        except errors.ConnectionError:
            print_and_log("No server found, connection error")
        except errors.InvalidConfigurationError:
            print_and_log("Invalid configuration")
            quit()
        except errors.InvalidTopicError:
            print_and_log(
                "Invalid topic, to enable auto creation of topics set"
                " auto.create.topics.enable to false in broker configuration"
            )
        finally:
            print_and_log("Retrying in 10s")
            sleep(10)
            # Recursive call after waiting
            self._set_up_producer(server)

    def add_config(self, pvs: List[str]) -> None:
        """
        Create a forwarder configuration to add more pvs to be monitored.

        :param pvs: A list of new PVs to add to the forwarder configuration.
        """
        message_buffer = self.converter.create_forwarder_configuration(pvs)
        self.producer.send(self.topic, message_buffer)

    def topic_exists(self, topic_name: str) -> bool:
        return topic_name in self.client.topics()

    def remove_config(self, pvs: List[str]) -> None:
        """
        Create a forwarder configuration to remove pvs that are being monitored.

        :param pvs: A list of PVs to remove from the forwarder configuration.
        """
        message_buffer = self.converter.remove_forwarder_configuration(pvs)
        self.producer.send(self.topic, message_buffer)

    def stop_all_pvs(self) -> None:
        """
        Sends a stop_all command to the forwarder to clear all configuration.
        """
        message_buffer = self.converter.remove_all_forwarder_configuration()
        self.producer.send(self.topic, message_buffer)
