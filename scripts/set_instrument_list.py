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
import os
import sys
from typing import Literal, TypedDict

try:
    from server_common.channel_access import ChannelAccess
    from server_common.utilities import compress_and_hex, dehex_and_decompress
except ImportError:
    sys.path.append(
        os.path.join(os.path.dirname(sys.path[0]))
    )  # to allow server common from dir below
    from server_common.channel_access import ChannelAccess
    from server_common.utilities import compress_and_hex, dehex_and_decompress


def set_env() -> None:
    epics_ca_addr_list = "EPICS_CA_ADDR_LIST"
    """ If we're not in an EPICS terminal, add the address list to the set of
    environment keys """
    if epics_ca_addr_list not in os.environ.keys():
        os.environ[epics_ca_addr_list] = "127.255.255.255 130.246.51.255"
    print(epics_ca_addr_list + " = " + str(os.environ.get(epics_ca_addr_list)))


TS1 = "TS1"
TS2 = "TS2"
MUON_TARGET = "MUON"
MISC = "MISC"


class Instrument(TypedDict):
    name: str
    hostName: str
    pvPrefix: str
    isScheduled: bool
    groups: list[str]
    seci: Literal[False]
    targetStation: str


def inst_dictionary(
    instrument_name: str,
    hostname_prefix: str = "NDX",
    hostname: str | None = None,
    pv_prefix: str | None = None,
    is_scheduled: bool = True,
    groups: list[str] | None = None,
    target_station: str = MISC,
) -> Instrument:
    """
    Generate the instrument dictionary for the instrument list
    Args:
        instrument_name: instrument name
        hostname_prefix: prefix for hostname (defaults to NDX)
        hostname: whole host name overrides prefix, defaults to hostname_prefix + instrument name
        pv_prefix: the pv prefeix; default to IN:instrument_name
        is_scheduled: whether the instrument has scheduled users,
          and so should have user details written to it;
        groups: which science groups (e.g. SANS, MUONS) this instrument is in.
        target_station: the target station or "MISC" if no target station

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

    return {
        "name": instrument_name,
        "hostName": hostname_to_use,
        "pvPrefix": pv_prefix_to_use,
        "isScheduled": is_scheduled,
        "groups": groups_to_use,
        "seci": False,
        "targetStation": target_station,
    }


def set_instlist(instruments_list: list[Instrument], pv_address: str) -> None:
    new_value = json.dumps(instruments_list)
    new_value_compressed = compress_and_hex(new_value)

    ChannelAccess.caput(pv_address, new_value_compressed, True)
    # Type ignore here because caget WILL return a string due to the as_string argument,
    # but the signature says it can return lots of different types.
    result_compr: str = ChannelAccess.caget(pv_address, True)  # type: ignore
    result = dehex_and_decompress(bytes(result_compr, encoding="utf8")).decode("utf-8")

    if result != new_value:
        print("Warning! Entered value does not match new value for {0}".format(pv_address))
        print("Entered value: " + new_value)
        print("Actual value: " + result)
    else:
        print("Success! Updated value for {0}".format(pv_address))


MUONS = "MUONS"
EXCITATIONS = "EXCITATIONS"
SANS = "SANS"
ENGINEERING = "ENGINEERING"
MOLSPEC = "MOLSPEC"
CRYSTALLOGRAPHY = "CRYSTALLOGRAPHY"
SUPPORT = "SUPPORT"
DISORDERED = "DISORDERED"
REFLECTOMETRY = "REFLECTOMETRY"

if __name__ == "__main__":
    set_env()

    # The PV address list
    pv_address = "CS:INSTLIST"
    # Any instrument on here that has a EPICS/genie/GUI version
    # other than 12.0.01 or 13.0.1 http://beamlog.nd.rl.ac.uk/inst_summary.xml,
    # plus OFFSPEC and MUSR for the moment
    # instrument list values to set (uses utility to return the dictionary,
    # but you can use a dictionary directly)
    instruments_list = [
        inst_dictionary("ARGUS", groups=[MUONS], target_station=MUON_TARGET),
        inst_dictionary("CHRONUS", groups=[MUONS], target_station=MUON_TARGET),
        inst_dictionary("HIFI", groups=[MUONS], target_station=MUON_TARGET),
        inst_dictionary("CHIPIR", groups=[EXCITATIONS], target_station=TS2),
        inst_dictionary(
            "CRYOLAB_R80",
            groups=[SUPPORT],
            pv_prefix="IN:CRYOLA7E:",
            is_scheduled=False,
            target_station=MISC,
        ),
        inst_dictionary("DCLAB", groups=[SUPPORT], is_scheduled=False, target_station=MISC),
        inst_dictionary("LARMOR", groups=[SANS], target_station=TS2),
        inst_dictionary("ALF", groups=[EXCITATIONS], target_station=TS1),
        inst_dictionary("DEMO", groups=[], is_scheduled=False, target_station=MISC),
        inst_dictionary("IMAT", groups=[ENGINEERING], target_station=TS2),
        inst_dictionary("MUONFE", groups=[MUONS], is_scheduled=False, target_station=MUON_TARGET),
        inst_dictionary("ZOOM", groups=[SANS], target_station=TS2),
        inst_dictionary("IRIS", groups=[MOLSPEC], target_station=TS1),
        inst_dictionary(
            "IRIS_SETUP",
            groups=[MOLSPEC],
            pv_prefix="IN:IRIS_S29:",
            is_scheduled=False,
            target_station=TS1,
        ),
        inst_dictionary(
            "ENGINX_SETUP",
            groups=[ENGINEERING],
            pv_prefix="IN:ENGINX49:",
            is_scheduled=False,
            target_station=TS1,
        ),
        inst_dictionary(
            "HRPD_SETUP",
            groups=[CRYSTALLOGRAPHY],
            pv_prefix="IN:HRPD_S3D:",
            is_scheduled=False,
            target_station=MISC,
        ),
        inst_dictionary("HRPD", groups=[CRYSTALLOGRAPHY], target_station=MISC, is_scheduled=False),
        inst_dictionary("POLARIS", groups=[CRYSTALLOGRAPHY], target_station=TS1),
        inst_dictionary("VESUVIO", groups=[MOLSPEC], target_station=TS1),
        inst_dictionary("ENGINX", groups=[ENGINEERING, CRYSTALLOGRAPHY], target_station=TS1),
        inst_dictionary("MERLIN", groups=[EXCITATIONS], target_station=TS1),
        inst_dictionary("RIKENFE", groups=[MUONS], is_scheduled=False, target_station=MUON_TARGET),
        inst_dictionary("SELAB", groups=[SUPPORT], is_scheduled=False, target_station=MISC),
        inst_dictionary("EMMA-A", groups=[SUPPORT], is_scheduled=False, target_station=TS1),
        inst_dictionary("EMMA-B", groups=[SUPPORT], is_scheduled=False, target_station=TS1),
        inst_dictionary("SANDALS", groups=[DISORDERED], target_station=TS1),
        inst_dictionary("GEM", groups=[DISORDERED, CRYSTALLOGRAPHY], target_station=TS1),
        inst_dictionary("MAPS", groups=[EXCITATIONS], target_station=TS1),
        inst_dictionary("OSIRIS", groups=[MOLSPEC], target_station=TS1),
        inst_dictionary("INES", groups=[ENGINEERING], target_station=TS1),
        inst_dictionary("SXD", groups=[CRYSTALLOGRAPHY], target_station=TS1),
        inst_dictionary("TOSCA", groups=[MOLSPEC], target_station=TS1),
        inst_dictionary("LOQ", groups=[SANS], target_station=TS1),
        inst_dictionary("LET", groups=[EXCITATIONS], target_station=TS2),
        inst_dictionary("MARI", groups=[EXCITATIONS], target_station=TS1),
        inst_dictionary("CRISP", groups=[REFLECTOMETRY], is_scheduled=False, target_station=TS1),
        inst_dictionary("SOFTMAT", groups=[SUPPORT], is_scheduled=False, target_station=MISC),
        inst_dictionary("SURF", groups=[REFLECTOMETRY], target_station=TS1),
        inst_dictionary("NIMROD", groups=[DISORDERED], target_station=TS2),
        inst_dictionary(
            "DETMON",
            groups=[SUPPORT],
            hostname_prefix="NDA",
            is_scheduled=False,
            pv_prefix="TE:NDADETF1:",
            target_station=MISC,
        ),
        inst_dictionary("EMU", groups=[MUONS], target_station=MUON_TARGET),
        inst_dictionary("INTER", groups=[REFLECTOMETRY], target_station=TS2),
        inst_dictionary("POLREF", groups=[REFLECTOMETRY], target_station=TS2),
        inst_dictionary("SANS2D", groups=[SANS], target_station=TS2),
        inst_dictionary("MUSR", groups=[MUONS], target_station=MUON_TARGET),
        inst_dictionary("MUX", groups=[MUONS], target_station=MUON_TARGET),
        inst_dictionary("WISH", groups=[CRYSTALLOGRAPHY], target_station=TS2),
        inst_dictionary(
            "WISH_SETUP",
            groups=[CRYSTALLOGRAPHY],
            pv_prefix="IN:WISH_S9C:",
            is_scheduled=False,
            target_station=TS2,
        ),
        inst_dictionary("PEARL", groups=[CRYSTALLOGRAPHY], target_station=TS1),
        inst_dictionary(
            "PEARL_SETUP",
            groups=[CRYSTALLOGRAPHY],
            pv_prefix="IN:PEARL_5B:",
            is_scheduled=False,
            target_station=TS1,
        ),
        inst_dictionary(
            "HIFI-CRYOMAG",
            groups=[MUONS],
            pv_prefix="IN:HIFI-C11:",
            is_scheduled=False,
            target_station=MUON_TARGET,
        ),
        inst_dictionary("OFFSPEC", groups=[REFLECTOMETRY], target_station=TS2),
        inst_dictionary("MOTION", groups=[SUPPORT], is_scheduled=False, target_station=MISC),
        inst_dictionary("SCIDEMO", groups=[SUPPORT], is_scheduled=False, target_station=MISC),
        inst_dictionary(
            "IBEXGUITEST",
            groups=[SUPPORT],
            pv_prefix="IN:IBEXGUAD:",
            is_scheduled=False,
            target_station=MISC,
        ),
    ]

    set_instlist(instruments_list, pv_address)

    # set group based PVs
    groups = set()
    for inst in instruments_list:
        groups.update(inst["groups"])

    for g in sorted(groups):
        pv_address = f"CS:INSTLIST:{g}"
        inst_list = [x for x in instruments_list if g in x["groups"]]
        set_instlist(inst_list, pv_address)
