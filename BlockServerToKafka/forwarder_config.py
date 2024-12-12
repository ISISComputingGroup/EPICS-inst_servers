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
from typing import List

from streaming_data_types.fbschemas.forwarder_config_update_fc00.Protocol import (
    Protocol,
)
from streaming_data_types.fbschemas.forwarder_config_update_fc00.UpdateType import (
    UpdateType,
)
from streaming_data_types.forwarder_config_update_fc00 import StreamInfo, serialise_fc00


class ForwarderConfig:
    """
    Class that converts the pv information to a forwarder config message payload
    """

    def __init__(
        self,
        topic: str,
        epics_protocol: Protocol = Protocol.CA,  # pyright: ignore
        schema: str = "f144",
    ) -> None:
        self.schema = schema
        self.topic = topic
        self.epics_protocol = epics_protocol

    def _create_streams(self, pvs: List[str]) -> List[StreamInfo]:
        return [StreamInfo(pv, self.schema, self.topic, self.epics_protocol, 0) for pv in pvs]  # pyright: ignore

    def create_forwarder_configuration(self, pvs: List[str]) -> bytes:
        return serialise_fc00(UpdateType.ADD, self._create_streams(pvs))  # pyright: ignore

    def remove_forwarder_configuration(self, pvs: List[str]) -> bytes:
        return serialise_fc00(UpdateType.REMOVE, self._create_streams(pvs))  # pyright: ignore

    @staticmethod
    def remove_all_forwarder_configuration() -> bytes:
        return serialise_fc00(UpdateType.REMOVEALL, [])  # pyright: ignore
