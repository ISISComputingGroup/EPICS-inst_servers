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
from typing import Dict, Union

from server_common.helpers import PVPREFIX_MACRO


class Block:
    """Contains all the information about a block.

    Attributes:
        name (string): The block name
        pv (string): The PV pointed at
        local (bool): Whether the PV is local to the instrument
        visible (bool): Whether the block should be shown
        component (string): The component the block belongs to
        runcontrol (bool): Whether run-control is enabled
        lowlimit (float): The low limit for run-control
        highlimit (float): The high limit for run-control
        log_periodic (bool): Whether the block is sampled periodically in the archiver
        log_rate (float): Time between archive samples (in seconds)
        log_deadband (float): Deadband for the block to be archived
        alarmenabled (bool): Whether the alarm should be enabled
        alarmlatched (bool): Whether the alarm should be latched
        alarmdelay (float): The delay for trigerring alarm
        alarmguidance (string): The guidance for the alarm

    """

    def __init__(
        self,
        name: str,
        pv: str,
        local: bool = True,
        visible: bool = True,
        component: str = None,
        runcontrol: bool = False,
        lowlimit: float = None,
        highlimit: float = None,
        suspend_on_invalid: bool = False,
        log_periodic: bool = False,
        log_rate: float = 5,
        log_deadband: float = 0,
        set_block: bool = False,
        set_block_val: str = None,
        alarmenabled: bool = False,
        alarmlatched: bool = False,
        alarmdelay: float = None,
        alarmguidance: str = None,
    ):
        """Constructor.

        Args:
            name: The block name
            pv: The PV pointed at
            local: Whether the PV is local to the instrument
            visible: Whether the block should be shown
            component: The component the block belongs to
            runcontrol: Whether run-control is enabled
            lowlimit: The low limit for run-control
            highlimit: The high limit for run-control
            suspend_on_invalid: Whether to suspend run-control on invalid values
            log_periodic: Whether the block is sampled periodically in the archiver
            log_rate: Time between archive samples (in seconds)
            log_deadband: Deadband for the block to be archived
            set_block: whether the block should be set upon config change
            set_block_val: what the block should be set to upon config change
            alarmenabled (bool): Whether the alarm should be enabled
            alarmlatched (bool): Whether the alarm should be latched
            alarmdelay (float): The delay for trigerring alarm
            alarmguidance (string): The guidance for the alarm
        """
        self.name = name
        self.pv = pv
        self.local = local
        self.visible = visible
        self.component = component
        self.rc_lowlimit = lowlimit
        self.rc_highlimit = highlimit
        self.rc_enabled = runcontrol
        self.rc_suspend_on_invalid = suspend_on_invalid
        self.log_periodic = log_periodic
        self.log_rate = log_rate
        self.log_deadband = log_deadband
        self.set_block = set_block
        self.set_block_val = set_block_val
        self.alarmenabled = alarmenabled
        self.alarmlatched = alarmlatched
        self.alarmdelay = alarmdelay
        self.alarmguidance = alarmguidance


    def _get_pv(self) -> str:
        pv_name = self.pv
        # Check starts with as may have already been provided
        if self.local and not pv_name.startswith(PVPREFIX_MACRO):
            pv_name = PVPREFIX_MACRO + self.pv
        return pv_name

    def set_visibility(self, visible: bool):
        """Toggle the visibility of the block.

        Args:
            visible: Whether the block is visible or not
        """
        self.visible = visible

    def __str__(self):
        set_block_str = ""
        if self.set_block:
            set_block_str = f", SetBlockVal: {self.set_block_val}"
        return (
            f"Name: {self.name}, PV: {self.pv}, Local: {self.local}, Visible: {self.visible}, Component: {self.component}"
            f", RCEnabled: {self.rc_enabled}, RCLow: {self.rc_lowlimit}, RCHigh: {self.rc_highlimit}{set_block_str}"
        )

    def to_dict(self) -> Dict[str, Union[str, float, bool]]:
        """Puts the block's details into a dictionary.

        Returns:
            The block's details
        """
        return {
            "name": self.name,
            "pv": self._get_pv(),
            "local": self.local,
            "visible": self.visible,
            "component": self.component,
            "runcontrol": self.rc_enabled,
            "lowlimit": self.rc_lowlimit,
            "highlimit": self.rc_highlimit,
            "log_periodic": self.log_periodic,
            "log_rate": self.log_rate,
            "log_deadband": self.log_deadband,
            "suspend_on_invalid": self.rc_suspend_on_invalid,
            "set_block": self.set_block,
            "set_block_val": self.set_block_val,
            "alarmenabled": self.alarmenabled,
            "alarmlatched": self.alarmlatched,
            "alarmdelay": self.alarmdelay,
            "alarmguidance": self.alarmguidance,
        }
