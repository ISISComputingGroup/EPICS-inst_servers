import json
import os
import sys

from server_common.ioc_data_source import IocDataSource
from server_common.mysql_abstraction_layer import SQLAbstraction
from server_common.utilities import print_and_log, SEVERITY


def register_ioc_start(ioc_name, pv_database=None, prefix=None):
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
        print_and_log("Error registering ioc start: {}: {}".format(e.__class__.__name__, e), SEVERITY.MAJOR)


def get_macro_values():
    """
    Parse macro environment JSON into dict. To make this work use the icpconfigGetMacros program.

    Returns: Macro Key:Value pairs as dict
    """
    macros = json.loads(os.environ.get("REFL_MACROS", "{}"))
    macros = {key: value for (key, value) in macros.items()}
    # Get macros set by IocTestFramework
    test_devsim = os.environ.get("TESTDEVSIM", "no").lower() == "yes"
    test_recsim = os.environ.get("TESTRECSIM", "no").lower() == "yes"
    if test_devsim or test_recsim:
        # Set macros as is done in EPICS/iocstartup/ioctesting.cmd
        macros["DEVSIM"] = "1" if test_devsim else "0"
        macros["RECSIM"] = "1" if test_recsim else "0"
        macros["SIMULATE"] = "1"
        macros["SIMSFX"] = "_RECSIM" if test_recsim else "_DEVSIM"
        # Load macros from test_config.txt
        test_macros_filepath = os.path.join(os.getenv("ICPVARDIR", r"C:\Instrument\Var"), "tmp", "test_config.txt")
        if os.path.exists(test_macros_filepath):
            with open(test_macros_filepath, mode="r") as test_macros_file:
                for line in test_macros_file.readlines():
                    split_line = line.split('"')
                    macro_name = split_line[1]
                    macro_value = split_line[3]
                    macros[macro_name] = macro_value
    print("Defined macros: " + str(macros))
    return macros
