#This file is part of the ISIS IBEX application.
#Copyright (C) 2012-2016 Science & Technology Facilities Council.
#All rights reserved.
#
#This program is distributed in the hope that it will be useful.
#This program and the accompanying materials are made available under the
#terms of the Eclipse Public License v1.0 which accompanies this distribution.
#EXCEPT AS EXPRESSLY SET FORTH IN THE ECLIPSE PUBLIC LICENSE V1.0, THE PROGRAM 
#AND ACCOMPANYING MATERIALS ARE PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES 
#OR CONDITIONS OF ANY KIND.  See the Eclipse Public License v1.0 for more details.
#
#You should have received a copy of the Eclipse Public License v1.0
#along with this program; if not, you can obtain a copy from
#https://www.eclipse.org/org/documents/epl-v10.php or 
#http://opensource.org/licenses/eclipse-1.0.php
import zlib
import sys
import os
try:
    from server_common.channel_access import ChannelAccess as ca
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(sys.path[0])))  # to allow server common from dir below
    from server_common.channel_access import ChannelAccess as ca


class Log:
    def error(self, message):
        print(f"ERROR: {message}")

    def info(self, message):
        print(f"INFO : {message}")


LOG = Log()


class InstrumentStatus:

    def __init__(self, pv_prefix=None):
        if pv_prefix is None:
            self._prefix = os.getenv("MYPVPREFIX", "")
        else:
            self._prefix = pv_prefix
        LOG.info(f"PVPREFIX: {self._prefix}")

        # If we're not in an EPICS terminal, add the address list to the set of environment keys
        epics_ca_addr_list = "EPICS_CA_ADDR_LIST"
        if not epics_ca_addr_list in os.environ.keys():
            os.environ[epics_ca_addr_list] = "127.255.255.255 130.246.51.255"
        LOG.info(epics_ca_addr_list + " = " + str(os.environ.get(epics_ca_addr_list)))

    def check(self):

        if not self._check_PV_compressed_hex("CS:BLOCKSERVER:SERVER_STATUS", "Check block server status",
                                             help_text="Check C:\Instrument\Var\logs\ioc\BLOCKSVR-<todays date>.log",
                                             allowed_values=['{"status": ""}']):
            return "Blockserver not started"
        return "OK"

    def _check_PV_compressed_hex(self, pv_name, description, help_text="", allowed_values=None):
        full_pv = f"{self._prefix}{pv_name}"
        value = ca.caget(full_pv)
        if value is None:
            LOG.error(f"{description}: Fail PV can not be read")
            LOG.error(f"    {help_text}")
            return False

        try:
            uncompressed_val = zlib.decompress(value.decode("hex"))
        except Exception as ex:
            #TODO: untried
            LOG.error(f"{full_pv}={value}")
            LOG.error(f"{description}: Fail to decompress PV with error - {ex}")
            return False

        if allowed_values is not None and uncompressed_val not in allowed_values:
            LOG.error(f"{full_pv}={uncompressed_val}")
            LOG.error(f"{description}: Fail PV has invalid value must be one of {allowed_values}")
            LOG.error(f"    {help_text}")
            return False

        return True


if __name__ == "__main__":
    status = InstrumentStatus("TE:NDW1407:").check()
    LOG.info(status)
