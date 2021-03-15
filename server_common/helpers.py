import json
import os
import sys
from contextlib2 import contextmanager

from server_common.channel_access import ChannelAccess
from server_common.ioc_data_source import IocDataSource
from genie_python.mysql_abstraction_layer import SQLAbstraction
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
    macros = json.loads(os.environ.get("MACROS", "{}"))
    macros = {key: value for (key, value) in macros.items()}
    print("Defined macros: " + str(macros))
    return macros


@contextmanager
def motor_in_set_mode(motor_pv):
    """
    Uses a context to place motor into set mode and ensure that it leaves set mode after context has ended. If it
    can not set the mode correctly will not run the yield.
    Args:
        motor_pv: motor pv on which to set the mode

    Returns:
    """

    calibration_set_pv = "{}.SET".format(motor_pv)
    offset_freeze_switch_pv = "{}.FOFF".format(motor_pv)

    try:
        ChannelAccess.caput_retry_on_fail(calibration_set_pv, "Set")
        offset_freeze_switch = ChannelAccess.caget(offset_freeze_switch_pv)
        ChannelAccess.caput_retry_on_fail(offset_freeze_switch_pv, "Frozen")
    except IOError as ex:
        raise ValueError("Can not set motor set and frozen offset mode: {}".format(ex))

    try:
        yield
    finally:
        try:
            ChannelAccess.caput_retry_on_fail(calibration_set_pv, "Use")
            ChannelAccess.caput_retry_on_fail(offset_freeze_switch_pv, offset_freeze_switch)
        except IOError as ex:
            raise ValueError("Can not reset motor set and frozen offset mode: {}".format(ex))
