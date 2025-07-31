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
from server_common.utilities import SEVERITY, print_and_log
from streaming_data_types.fbschemas.forwarder_config_update_fc00.Protocol import (
    Protocol,
)

from BlockServerToKafka.forwarder_config import ForwarderConfig


class ProducerWrapper:
    """
    A wrapper class for the kafka producer.
    """

    def __init__(
        self,
        server: str,
        config_topic: str,
        data_topic: str,
        epics_protocol: Protocol = Protocol.CA,  # pyright: ignore
    ) -> None:
        self.topic = config_topic
        self.converter = ForwarderConfig(data_topic, epics_protocol)
        while not self._set_up_producer(server):
            print_and_log("Failed to create producer, retrying in 30s")
            sleep(30)

    def _set_up_producer(self, server: str) -> bool:
        """
        Attempts to create a Kafka producer and consumer. Retries with a recursive call every 30s.
        """
        try:
            self.client = KafkaConsumer(bootstrap_servers=server)
            self.producer = KafkaProducer(bootstrap_servers=server)
            if not self.topic_exists(self.topic):
                print_and_log(
                    f"WARNING: topic {self.topic} does not exist. It will be created by default."
                )
            return True
        except errors.NoBrokersAvailable:
            print_and_log(f"No brokers found on server: {server[0]}", severity=SEVERITY.MAJOR)
        except errors.KafkaConnectionError:
            print_and_log("No server found, connection error", severity=SEVERITY.MAJOR)
        except errors.InvalidConfigurationError:
            print_and_log("Invalid configuration", severity=SEVERITY.MAJOR)
            quit()
        except errors.InvalidTopicError:
            print_and_log(
                "Invalid topic, to enable auto creation of topics set"
                " auto.create.topics.enable to false in broker configuration",
                severity=SEVERITY.MAJOR,
            )
        except Exception as e:
            print_and_log(
                f"Unexpected error while creating producer or consumer: {str(e)}",
                severity=SEVERITY.MAJOR,
            )
        return False

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
