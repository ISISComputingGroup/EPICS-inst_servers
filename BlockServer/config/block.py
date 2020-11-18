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

from BlockServer.core.macros import PVPREFIX_MACRO
import copy


class Block:
    """ Contains all the information about a block.

        Attributes:
            name (string): The block name
            pv (string): The PV pointed at
            local (bool): Whether the PV is local to the instrument
            visible (bool): Whether the block should be shown
            component (string): The component the block belongs to

            runcontrol (bool): Whether run-control is enabled
            lowlimt (float): The low limit for run-control
            highlimit (float): The high limit for run-control

            arch_periodic (bool): Whether the block is sampled periodically in the archiver
            arch_rate (float): Time between archive samples (in seconds)
            arch_deadband (float): Deadband for the block to be archived
    """
    def __init__(self, name, pv, local=True, visible=True, component=None, runcontrol=False, lowlimit=None,
                 highlimit=None, suspend_on_invalid=False, log_periodic=False, log_rate=5, log_deadband=0):
        """ Constructor.

        Args:
            name (string): The block name
            pv (string): The PV pointed at
            local (bool): Whether the PV is local to the instrument
            visible (bool): Whether the block should be shown
            component (string): The component the block belongs to

            runcontrol (bool): Whether run-control is enabled
            lowlimt (float): The low limit for run-control
            highlimit (float): The high limit for run-control
            suspend_on_invalid (bool): Whether to suspend run-control on invalid values

            arch_periodic (bool): Whether the block is sampled periodically in the archiver
            arch_rate (float): Time between archive samples (in seconds)
            arch_deadband (float): Deadband for the block to be archived
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

    def _get_pv(self):
        pv_name = self.pv
        # Check starts with as may have already been provided
        if self.local and not pv_name.startswith(PVPREFIX_MACRO):
            pv_name = PVPREFIX_MACRO + self.pv
        return pv_name

    def set_visibility(self, visible):
        """ Toggle the visibility of the block.

        Args:
            visible (bool): Whether the block is visible or not
        """
        self.visible = visible

    def __str__(self):
        return f"Name: {self.name}, PV: {self.pv}, Local: {self.local}, Visible: {self.visible}, Component: {self.component}" \
               f", RCEnabled: {self.rc_enabled}, RCLow: {self.rc_lowlimit}, RCHigh: {self.rc_highlimit}"

    def to_dict(self):
        """ Puts the block's details into a dictionary.

        Returns:
            dict : The block's details
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
        }
