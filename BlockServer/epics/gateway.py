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
import re
import time
from shutil import copyfile

from server_common.channel_access import ChannelAccess
from server_common.helpers import CONTROL_SYSTEM_PREFIX
from server_common.utilities import print_and_log

ALIAS_HEADER = """\
##
EVALUATION ORDER ALLOW, DENY

"""

ALIAS_FOOTER = r"""
## serve blockserver internal variables, including Flag variables needed by blockserver process to restart gateway
{0}CS:GATEWAY:BLOCKSERVER:.*    				    ALLOW	ANYBODY	    1
## allow anybody to generate gateway reports
{0}CS:GATEWAY:BLOCKSERVER:report[1-9]Flag		ALLOW	ANYBODY		1
## ignore any request related to run control/alerts etc. (RC,AC,DC) on blocks, these are handled by RUNCTRL ioc
{0}CS:SB:[^:]*:[ADR]C:.*                     DENY
## ignore any request not related to local blocks or gateway itself
!{0}CS:\(SB\|GATEWAY\):.*                    DENY
"""


def build_block_alias_lines(full_block_pv, pv_suffix, underlying_pv, include_comments=True):
    lines = list()
    if underlying_pv.endswith(":SP"):
        # The block points at a setpoint
        if include_comments:
            lines.append(
                "## The block points at a :SP, so it needs an optional group as "
                "genie_python will append an additional :SP"
            )

        full_block_pv = r"{}\(:SP\)?".format(full_block_pv)

        # Pattern match is for picking up any extras like :RBV or .EGU
        lines.append(f"{full_block_pv}\\([.:].*\\)    ALIAS    {underlying_pv}\\2")
    elif pv_suffix is not None:
        # The block points at a readback value (most likely for a motor)
        if include_comments:
            lines.append(
                f"## The block points at a {pv_suffix} field, so it needs entries for both reading the field "
                f"and for the rest"
            )

        # Pattern match is for picking up any extras like :RBV or .EGU
        lines.append(
            f"{full_block_pv}\\([.:].*\\)    ALIAS    {underlying_pv.replace(pv_suffix, '')}\\1"
        )
        lines.append(f"{full_block_pv}[.]VAL    ALIAS    {underlying_pv}")
    else:
        # Standard case
        if include_comments:
            lines.append(
                "## Standard block with entries for matching :SP and :SP:RBV as well as .EGU"
            )

        # Pattern match is for picking up any any SP or SP:RBV
        lines.append(f"{full_block_pv}\\([.:].*\\)    ALIAS    {underlying_pv}\\1")
    lines.append(f"{full_block_pv}    ALIAS    {underlying_pv}")
    return lines


class Gateway:
    """A class for interacting with the EPICS gateway that creates the aliases used for implementing blocks"""

    def __init__(
        self,
        gateway_prefix,
        instrument_prefix,
        pvlist_file,
        block_prefix,
        control_sys_prefix=CONTROL_SYSTEM_PREFIX,
    ):
        """Constructor.

        Args:
            gateway_prefix (string): The full prefix for the gateway, including the instrument prefix etc.
            instrument_prefix (string): Prefix for instrument PVs
            pvlist_file (string): Where to write the gateway file
            block_prefix (string): The prefix for information about a block, including the instrument_prefix etc.
            control_sys_prefix (string): The prefix for the control system, including the instrument_prefix etc.
        """
        self._gateway_prefix = gateway_prefix
        self._block_prefix = block_prefix
        self._pvlist_file = pvlist_file
        self._inst_prefix = instrument_prefix
        self._control_sys_prefix = control_sys_prefix

    def exists(self):
        """Checks the gateway exists by querying one of the PVs.

        Returns:
            bool : Whether the gateway is running and is accessible
        """
        return ChannelAccess.caget(self._gateway_prefix + "pvtotal") is not None

    def _reload(self):
        print_and_log("Reloading gateway")
        try:
            # Have to wait after put as the gateway does not do completion callbacks (it is not an IOC)
            ChannelAccess.caput(self._gateway_prefix + "newAsFlag", 1)

            while ChannelAccess.caget(self._gateway_prefix + "newAsFlag") == 1:
                time.sleep(1)
            print_and_log("Gateway reloaded")
        except Exception as err:
            print_and_log(f"Problem with reloading the gateway {err}")

    def _generate_alias_file(self, blocks=None):
        # Generate blocks.pvlist for gateway
        with open(self._pvlist_file, "w") as f:
            header = ALIAS_HEADER.format(self._inst_prefix)
            f.write(header)
            if blocks is not None:
                for name, value in blocks.items():
                    lines = self.generate_alias(value.name, value.pv, value.local)
                    f.write("\n".join(lines) + "\n")
            f.write(ALIAS_FOOTER.format(self._inst_prefix))
            # Add a blank line at the end!
            f.write("\n")

    def generate_alias(self, block_name, underlying_pv, local):
        print_and_log(f"Creating block: {block_name} for {underlying_pv}")

        underlying_pv = underlying_pv.replace(".VAL", "")

        # Look for a field name in PV
        match = re.match(r".*(\.[A-Z0-9]+)$", underlying_pv)
        pv_suffix = match.group(1) if match else None

        # If it's local we need to add this instrument's prefix
        if local:
            underlying_pv = f"{self._inst_prefix}{underlying_pv}"

        # Add on all the prefixes
        full_block_pv = f"{self._block_prefix}{block_name}"

        lines = build_block_alias_lines(full_block_pv, pv_suffix, underlying_pv)

        # Create a case insensitive alias so clients don't have to worry about getting case right
        if full_block_pv != full_block_pv.upper():
            lines.append("## Add full caps equivalent so clients need not be case sensitive")
            lines.extend(
                build_block_alias_lines(full_block_pv.upper(), pv_suffix, underlying_pv, False)
            )

        lines.append("")  # New line to seperate out each block
        return lines

    def set_new_aliases(self, blocks, configures_block_gateway, config_dir):
        """Creates the aliases for the blocks and restarts the gateway.

        Args:
            blocks (OrderedDict): The blocks that belong to the configuration
            configures_block_gateway (bool): If true indicates that the config contains a gwblock.pvlist to configure
                the block gateway with.
            config_dir (str): The directory the configuration we are loading the blocks for lives in.
        """
        pvlist_file = os.path.join(config_dir, "gwblock.pvlist")
        if configures_block_gateway and os.path.exists(pvlist_file):
            print_and_log("Using {} to configure block gateway".format(pvlist_file))
            copyfile(pvlist_file, self._pvlist_file)
        elif configures_block_gateway:
            print_and_log("File: {} not found generating gwblock.pvlist".format(pvlist_file))
            self._generate_alias_file(blocks)
        else:
            self._generate_alias_file(blocks)
        self._reload()
