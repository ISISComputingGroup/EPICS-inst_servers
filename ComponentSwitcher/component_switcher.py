from __future__ import print_function, unicode_literals, division, absolute_import

import argparse
import copy
import functools
import json
import os
import time
import traceback
import types
import six
import sys

from concurrent.futures.thread import ThreadPoolExecutor
from typing import List, Dict, Any
from genie_python import genie as g

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from server_common.utilities import print_and_log as _common_print_and_log, dehex_and_decompress, compress_and_hex, \
    SEVERITY
from server_common.channel_access import ChannelAccess
from server_common.pv_names import BlockserverPVNames


print_and_log = functools.partial(_common_print_and_log, src="ComponentSwitcher")


CA_WORKER = ThreadPoolExecutor(1)


def wait_for_blockserver_operation_to_complete() -> None:
    while True:
        time.sleep(1)
        pv_data = ChannelAccess.caget(g.prefix_pv_name(f"CS:{BlockserverPVNames.SERVER_STATUS}"), as_string=True).encode("ascii")
        status = json.loads(dehex_and_decompress(pv_data))
        if status["status"] == "":
            print_and_log("Blockserver operation complete")
            break
        else:
            print_and_log("Waiting for blockserver operation to complete (status: {})".format(status["status"]))


def read_config_from_pv(pv: str) -> Dict[str, Any]:
    """
    Reads and deserializes a config from the blockserver
    """
    pv_data = ChannelAccess.caget(g.prefix_pv_name(pv), as_string=True).encode("ascii")
    return json.loads(dehex_and_decompress(pv_data))


def write_config_to_pv(pv: str, config: Dict[str, Any]) -> None:
    """
    Serializes and writes a config to the blockserver
    """
    data = compress_and_hex(json.dumps(config))
    ChannelAccess.caput(g.prefix_pv_name(pv), data, wait=True)
    wait_for_blockserver_operation_to_complete()


def config_modifier(func: types.FunctionType) -> types.FunctionType:
    @functools.wraps(func)
    def _inner(*args, **kwargs):

        current_config_name = get_current_config_name_from_blockserver()

        for config in get_configs_from_blockserver():
            print_and_log("Editing configuration {}".format(config["name"]))
            blockserver_config = read_config_from_pv(f"CS:{BlockserverPVNames.get_config_details_pv(config['pv'])}")
            modified_config = func(config=blockserver_config, *args, **kwargs)

            if config["name"] == current_config_name:
                write_config_to_pv(f"CS:{BlockserverPVNames.SET_CURR_CONFIG_DETAILS}", modified_config)
            else:
                write_config_to_pv(f"CS:{BlockserverPVNames.SAVE_NEW_CONFIG}", modified_config)

    return _inner


def get_current_config_name_from_blockserver() -> str:
    return ChannelAccess.caget(g.prefix_pv_name(f"CS:{BlockserverPVNames.CURR_CONFIG_NAME}"))


def get_configs_from_blockserver() -> List[Dict[str, str]]:
    """
    Returns a list of configuration names from the blockserver.
    """
    pv_data = ChannelAccess.caget(g.prefix_pv_name(f"CS:{BlockserverPVNames.CONFIGS}"), as_string=True)
    if pv_data is None:
        print_and_log("unable to get config names from blockserver. Assuming no configs exist.", SEVERITY.MAJOR)
        return []

    return json.loads(dehex_and_decompress(pv_data.encode("ascii")))


def remove_component_blocks(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove any blocks which come from components as opposed to the root configuration.
    """
    blocks = config["blocks"]
    config = copy.deepcopy(config)
    config["blocks"] = [block for block in blocks if block["component"] is None]
    return config


@config_modifier
def remove_component_from_all_configs(config: Dict[str, Any], component_name_to_be_removed: str) -> Dict[str, Any]:
    config = copy.deepcopy(config)

    components: List[Dict[str, str]] = config["components"]
    new_components: List[Dict[str, str]] = []

    for component in components:
        if component["name"] != component_name_to_be_removed:
            new_components.append(component)

    config["components"] = new_components
    return remove_component_blocks(config)


@config_modifier
def add_component_to_all_configurations(config: Dict[str, Any], component_name_to_be_added: str) -> Dict[str, Any]:
    config = copy.deepcopy(config)
    if not any(component["name"] == component_name_to_be_added for component in config["components"]):
        config["components"].append({"name": component_name_to_be_added})
    return remove_component_blocks(config)


def load_configswitcher_config_file(filename: str) -> List[Dict[str, Any]]:
    if os.path.exists(filename):
        with open(filename) as f:
            return json.loads(f.read())
    else:
        print("component_switcher config file does not exist - assuming empty config", SEVERITY.MAJOR)
        return []
    

def run_on_thread_and_print_exceptions(func: types.FunctionType) -> types.FunctionType:
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        def _inner():
            try:
                return func(*args, **kwargs)
            except Exception:
                print_and_log(traceback.format_exc())
        CA_WORKER.submit(_inner)
    return _wrapper


def create_monitors(config: List[Dict[str, Any]]) -> None:
    for item in config:
        pv = item["pv"]
        pv_is_local = item["is_local"]
        value_to_component_map = item["value_to_component_map"]

        if pv_is_local:
            pv = g.prefix_pv_name(pv)

        print_and_log("Adding monitor to PV {}".format(pv))

        def callback(val, *_, **__):
            """
            Callback function called when the monitored PV changes.
            """
            print_and_log("Got update for pv {}: {}".format(pv, val))
            for pv_value, component_name in value_to_component_map.items():
                if val != pv_value:
                    print_and_log("Removing component {} from all configurations".format(component_name))
                    remove_component_from_all_configs(component_name_to_be_removed=component_name)

            for pv_value, component_name in value_to_component_map.items():
                if val == pv_value:
                    print_and_log("Adding component {} to all configurations".format(component_name))
                    add_component_to_all_configurations(component_name_to_be_added=component_name)
                    break
            else:
                print_and_log("pv {} had value {} but this was not mapped to any component.".format(pv, val), SEVERITY.MAJOR)

        ChannelAccess.add_monitor(pv, run_on_thread_and_print_exceptions(callback))


def main() -> None:
    g.set_instrument(None)

    print_and_log("Starting ConfigSwitcher")

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Runs the component switcher.",
    )

    parser.add_argument("--pv_prefix", required=True, type=six.text_type,
                        help="The PV prefix of this instrument.")
    parser.add_argument("--config_file", type=six.text_type,
                        default=os.path.normpath(
                            os.path.join(os.getenv("ICPCONFIGROOT"), "ComponentSwitcher", "componentswitcher.json")),
                        help="The subsystem prefix to use for this remote IOC server")

    args = parser.parse_args()

    print("ComponentSwitcher starting, using config file {}".format(args.config_file))

    config = load_configswitcher_config_file(args.config_file)

    create_monitors(config)

    # Go into an infinite loop (not using any cpu time) to let the monitors happen in the background
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
