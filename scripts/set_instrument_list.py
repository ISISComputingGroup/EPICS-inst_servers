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

import json
import zlib
import sys
import os

try:
    from server_common.channel_access import ChannelAccess as ca
    from server_common.utilities import compress_and_hex, dehex_and_decompress
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(sys.path[0])))  # to allow server common from dir below
    from server_common.channel_access import ChannelAccess as ca
    from server_common.utilities import compress_and_hex, dehex_and_decompress


def set_env():
    epics_ca_addr_list = "EPICS_CA_ADDR_LIST"
    """ If we're not in an EPICS terminal, add the address list to the set of
    environment keys """
    if not epics_ca_addr_list in os.environ.keys():
        os.environ[epics_ca_addr_list] = "127.255.255.255 130.246.51.255"
    print(epics_ca_addr_list + " = " + str(os.environ.get(epics_ca_addr_list)))


def inst_dictionary(instrument_name, hostname_prefix="NDX", hostname=None, pv_prefix=None, is_scheduled=True, groups=None):
    """
    Generate the instrument dictionary for the instrument list
    Args:
        instrument_name: instrument name
        hostname_prefix: prefix for hostname (defaults to NDX)
        hostname: whole host name overrides prefix, defaults to hostname_prefix + instrument name
        pv_prefix: the pv prefeix; default to IN:instrument_name
        is_scheduled: whether the instrument has scheduled users and so should have user details written to it; default to True
        groups (List[str]): which science groups (e.g. SANS, MUONS) this instrument is in. Defaults to empty list

    Returns: dictionary for instrument

    """
    if hostname is not None:
        hostname_to_use = hostname
    else:
        hostname_to_use = hostname_prefix + instrument_name
    if pv_prefix is not None:
        pv_prefix_to_use = pv_prefix
    else:
        pv_prefix_to_use = "IN:{0}:".format(instrument_name)
        
    if groups is None:
        groups_to_use = []
    else:
        groups_to_use = groups
        
    return {"name": instrument_name,
            "hostName": hostname_to_use,
            "pvPrefix": pv_prefix_to_use,
            "isScheduled": is_scheduled,
            "groups": groups_to_use,
            }


def set_instlist(instruments_list, pv_address):
    new_value = json.dumps(instruments_list)
    new_value_compressed = compress_and_hex(new_value)

    ca.caput(pv_address, str(new_value_compressed), True)

    result_compr = ca.caget(pv_address, True)
    result = dehex_and_decompress(result_compr)

    print(result)

    if result != new_value:
        print("Warning! Entered value does not match new value.")
        print("Entered value: " + new_value)
        print("Actual value: " + result.decode("utf-8"))
    else:
        print("Success! The PV now reads: {0}".format(result))


if __name__ == "__main__":
    set_env()

    # The PV address list
    pv_address = "CS:INSTLIST"

    # instrument list values to set (uses utility to return the dictionary but you can use a dictionary directly)
    instruments_list = [
        inst_dictionary("LARMOR", groups=["SANS"]),
        inst_dictionary("ALF", groups=["EXCITATIONS"]),
        inst_dictionary("DEMO", groups=[], is_scheduled=False),
        inst_dictionary("IMAT", groups=["ENGINEERING"]),
        inst_dictionary("MUONFE", groups=["MUONS"], hostname_prefix="NDE", is_scheduled=False),
        inst_dictionary("ZOOM", groups=["SANS"]),
        inst_dictionary("IRIS", groups=["MOLSPEC"]),
        inst_dictionary("IRIS_SETUP", groups=["MOLSPEC"], pv_prefix="IN:IRIS_S29:", is_scheduled=False),
        inst_dictionary("ENGINX_SETUP", groups=["ENGINEERING"], pv_prefix="IN:ENGINX49:", is_scheduled=False),
        inst_dictionary("HRPD", groups=["CRYSTALLOGRAPHY"]),
        inst_dictionary("POLARIS", groups=["CRYSTALLOGRAPHY"]),
        inst_dictionary("VESUVIO", groups=["MOLSPEC"]),
        inst_dictionary("ENGINX", groups=["ENGINEERING", "CRYSTALLOGRAPHY"]),
        inst_dictionary("MERLIN", groups=["EXCITATIONS"]),
        inst_dictionary("RIKENFE", groups=["MUONS"], is_scheduled=False),
        inst_dictionary("SELAB", groups=["SUPPORT"], is_scheduled=False),
        inst_dictionary("EMMA-A", groups=["SUPPORT"], is_scheduled=False),
        inst_dictionary("SANDALS", groups=["DISORDERED"]),
        inst_dictionary("GEM", groups=["DISORDERED", "CRYSTALLOGRAPHY"]),
        inst_dictionary("MAPS", groups=["EXCITATIONS"]),
        inst_dictionary("OSIRIS", groups=["MOLSPEC"]),
        inst_dictionary("INES", groups=["CRYSTALLOGRAPHY"]),
        inst_dictionary("TOSCA", groups=["MOLSPEC"]),
        inst_dictionary("LOQ", groups=["SANS"]),
        inst_dictionary("LET", groups=["EXCITATIONS"]),
        inst_dictionary("MARI", groups=["EXCITATIONS"]),
        inst_dictionary("CRISP", groups=["REFLECTOMETRY"]),
        inst_dictionary("SOFTMAT", groups=["SUPPORT"], is_scheduled=False),
        inst_dictionary("SURF", groups=["REFLECTOMETRY"]),
        inst_dictionary("NIMROD", groups=["DISORDERED"]),
        inst_dictionary("DETMON", groups=["SUPPORT"], hostname_prefix="NDA", is_scheduled=False, pv_prefix="TE:NDADETF1:"),
        inst_dictionary("EMU", groups=["MUONS"]),
        inst_dictionary("INTER", groups=["REFLECTOMETRY"]),
        inst_dictionary("POLREF", groups=["REFLECTOMETRY"]),
        inst_dictionary("SANS2D", groups=["SANS"]),
		inst_dictionary("MUSR", groups=["MUONS"]),
    ]

    set_instlist(instruments_list, pv_address) 

    pv_address = "CS:INSTLIST:MUONS"
    instruments_list = [
        inst_dictionary("EMU"),
		inst_dictionary("MUSR"),
    ]
    set_instlist(instruments_list, pv_address) 

    pv_address = "CS:INSTLIST:EXCITATIONS"
    instruments_list = [
        inst_dictionary("MAPS"),
        inst_dictionary("MERLIN"),
        inst_dictionary("LET"),
        inst_dictionary("MARI"),
    ]
    set_instlist(instruments_list, pv_address) 

    pv_address = "CS:INSTLIST:DISORDERED"
    instruments_list = [
        inst_dictionary("SANDALS"),
        inst_dictionary("NIMROD"),
        inst_dictionary("GEM"),
    ]
    set_instlist(instruments_list, pv_address) 

    pv_address = "CS:INSTLIST:REFLECTOMETRY"
    instruments_list = [
        inst_dictionary("CRISP"),
        inst_dictionary("SURF"),
        inst_dictionary("POLREF"),
    ]
    set_instlist(instruments_list, pv_address) 

    pv_address = "CS:INSTLIST:SANS"
    instruments_list = [
        inst_dictionary("ZOOM"),
        inst_dictionary("LOQ"),
        inst_dictionary("SANS2D"),
        inst_dictionary("LARMOR"),
    ]
    set_instlist(instruments_list, pv_address)

    pv_address = "CS:INSTLIST:MOLSPEC"
    instruments_list = [
        inst_dictionary("IRIS"),
        inst_dictionary("OSIRIS"),
        inst_dictionary("TOSCA"),
        inst_dictionary("VESUVIO"),
    ]
    set_instlist(instruments_list, pv_address)

    pv_address = "CS:INSTLIST:ENGINEERING"
    instruments_list = [
        inst_dictionary("IMAT"),
        inst_dictionary("ENGINX"),
    ]
    set_instlist(instruments_list, pv_address)
