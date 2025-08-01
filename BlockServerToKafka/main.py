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
import sys

sys.path.insert(0, os.path.abspath(os.getcwd()))
from argparse import ArgumentParser
from os import environ
from time import sleep

from BlockServerToKafka.block_server_monitor import BlockServerMonitor
from BlockServerToKafka.kafka_producer import ProducerWrapper

if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "-d",
        "--data",
        help="Kafka topic to send Block PV data to",
        type=str,
        default="_sampleEnv",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Kafka topic to send forwarder config to",
        type=str,
        default="forwarder_config",
    )
    parser.add_argument(
        "-r",
        "--runlog",
        help="Kafka topic to send run log PV data to",
        type=str,
        default="_runLog",
    )
    parser.add_argument(
        "-b",
        "--broker",
        help="Location of the Kafka brokers (host:port)",
        nargs="+",
        type=str,
        default="livedata.isis.cclrc.ac.uk:31092",
    )
    parser.add_argument(
        "-p",
        "--pvprefix",
        help="PV Prefix of the block server",
        type=str,
        default=environ["MYPVPREFIX"],
    )

    args = parser.parse_args()
    KAFKA_DATA = args.data
    KAFKA_RUNLOG = args.runlog
    KAFKA_CONFIG = args.config
    KAFKA_BROKER = args.broker
    PREFIX = args.pvprefix
    block_producer = ProducerWrapper(KAFKA_BROKER, KAFKA_CONFIG, KAFKA_DATA)
    monitor = BlockServerMonitor(f"{PREFIX}CS:BLOCKSERVER:BLOCKNAMES", PREFIX, block_producer)
    runlog_producer = ProducerWrapper(KAFKA_BROKER, KAFKA_CONFIG, KAFKA_RUNLOG)

    dae_prefix = f"{PREFIX}DAE:"
    runlog_producer.add_config(
        [
            f"{dae_prefix}COUNTRATE",
            f"{dae_prefix}BEAMCURRENT",
            f"{dae_prefix}GOODFRAMES",
            f"{dae_prefix}RAWFRAMES",
            f"{dae_prefix}GOODUAH",
            f"{dae_prefix}MEVENTS",
            f"{dae_prefix}TOTALCOUNTS",
            f"{dae_prefix}MONITORCOUNTS",
            f"{dae_prefix}NPRATIO",
            f"{dae_prefix}PERIOD",
            f"{dae_prefix}TOTALUAMPS",
            # todo how should we do run_status/icp_event/is_running/is_waiting?
        ]
    )

    while True:
        sleep(0.1)
