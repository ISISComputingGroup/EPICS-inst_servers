import json
import os
import sys
from typing import Dict

from genie_python import genie as g
from genie_python.mysql_abstraction_layer import SQLAbstraction

from server_common.ioc_data_source import IocDataSource
from server_common.utilities import SEVERITY, print_and_log


def register_ioc_start(
    ioc_name: str,
    pv_database: Dict[str, Dict[str, str]] = None,
    prefix: str | None = None,
) -> None:
    """
    A helper function to register the start of an ioc.
    Args:
        ioc_name: name of the ioc to start
        pv_database: doctionary of pvs in the iov
        prefix: prefix of pvs in this ioc
    """
    try:
        exepath = sys.argv[0]
        if pv_database is None:
            pv_database = {}
        if prefix is None:
            prefix = "none"

        ioc_data_source = IocDataSource(SQLAbstraction("iocdb", "iocdb", "$iocdb"))
        ioc_data_source.insert_ioc_start(ioc_name, os.getpid(), exepath, pv_database, prefix)
    except Exception as e:
        print_and_log(
            "Error registering ioc start: {}: {}".format(e.__class__.__name__, e),
            SEVERITY.MAJOR,
        )


def get_macro_values() -> Dict[str, str]:
    """
    Parse macro environment JSON into dict. To make this work use the icpconfigGetMacros program.

    Returns: Macro Key:Value pairs as dict
    """
    macros = json.loads(os.environ.get("MACROS", "{}"))
    macros = {key: value for (key, value) in macros.items()}
    print("Defined macros: " + str(macros))
    return macros


motor_in_set_mode = g.adv.motor_in_set_mode


def _get_env_var(name: str) -> str:
    try:
        return os.environ[name]
    except:
        return ""


MACROS = {
    "$(MYPVPREFIX)": _get_env_var("MYPVPREFIX"),
    "$(EPICS_KIT_ROOT)": _get_env_var("EPICS_KIT_ROOT"),
    "$(ICPCONFIGROOT)": _get_env_var("ICPCONFIGROOT"),
    "$(ICPVARDIR)": _get_env_var("ICPVARDIR"),
}
CONTROL_SYSTEM_PREFIX = MACROS["$(MYPVPREFIX)"] + "CS:"
PVPREFIX_MACRO = "$(MYPVPREFIX)"
BLOCK_PREFIX = "CS:SB:"
