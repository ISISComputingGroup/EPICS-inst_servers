"""
Functions for interacting with the database server.
"""
from server_common.utilities import dehex_and_decompress, print_and_log
from server_common.channel_access import ChannelAccess
from server_common.pv_names import DatabasePVNames
import json
import traceback


def get_iocs(prefix):
    """
    Get the list of available IOCs from DatabaseServer.

    Args:
        prefix : The PV prefix for this instrument.

    Returns:
        A list of the names of available IOCs.
    """
    #
    try:
        rawjson = dehex_and_decompress(ChannelAccess.caget(prefix + DatabasePVNames.IOCS)).decode("utf-8")
        return json.loads(rawjson).keys()
    except Exception:
        print_and_log(f"Could not retrieve IOC list: {traceback.format_exc()}", "MAJOR")
        return []
