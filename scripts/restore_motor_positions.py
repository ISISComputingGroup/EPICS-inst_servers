"""
Script to restore motor positions from the archive.
"""
import argparse
import os
import socket
import sys
from datetime import datetime, timedelta
from typing import Any, List, Optional, TextIO, Tuple

from genie_python import genie as g
from genie_python.mysql_abstraction_layer import SQLAbstraction

DATA_TIME_DISPLAY_FORMAT = "%Y-%m-%d %H:%M:%S"

SECONDS_IN_A_DAY = 24 * 60 * 60


# Default maximum controller to restore on
MAX_CONTROLLER = 10

# max axes number on a controller
MAX_AXIS = 8


try:
    LOG_DIR = os.path.join(os.environ["ICPVARDIR"], "logs")
except KeyError:
    LOG_DIR = os.getcwd()
LOG_FILENAME = os.path.join(LOG_DIR, f"restore_motor_positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

try:
    from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from ArchiverAccess.archiver_data_source import ArchiverDataSource, ArchiverDataValue
from server_common.helpers import motor_in_set_mode
from server_common.utilities import parse_date_time_arg_exit_on_fail


class Severity:
    """
    Get and translate the severity text from the database
    """
    # SQL to get names
    SEVERITY_NAMES_SQL = "SELECT severity_id, name FROM archive.severity"

    # list of severities
    alarm_severity_text = {}

    @staticmethod
    def get(severity_id):
        """
        Translate the severity id to text
        Args:
            severity_id: severity id

        Returns:
            text or the original number if it isn't defined in the text
        """
        return Severity.alarm_severity_text.get(severity_id, str(severity_id))

    @staticmethod
    def populate(archive_mysql_abstraction_layer):
        """
        Populate the severity class, must be called before get is called
        Args:
            archive_mysql_abstraction_layer: abstraction layer to call the database through
        """
        for severity_id, name in archive_mysql_abstraction_layer.query_returning_cursor(
                Severity.SEVERITY_NAMES_SQL, ()):
            Severity.alarm_severity_text[severity_id] = name.strip()


def print_and_log(message, log_file):
    """
    Write message to screen and log to file
    Args:
        message: message
        log_file: file to log to
    """
    print(message)
    log_file.write(message + "\n")


def get_archived_positions(pv_names: List[str], data_time: datetime, host: str,
                           check_movement_for=timedelta(hours=1)) \
                            -> List[Tuple[str, ArchiverDataValue, Optional[datetime]]]:
    """
    Get the values for the motors from the database
    Args:
        pv_names: base motor names
        data_time: time to get the data for
        host: host to get data from
        check_movement_for: time to check for motor movement

    Returns:
        list of pvs containing tuple of name, archiver data value of next move, and time at which value was found
    """
    archive_mysql_abstraction_layer = SQLAbstraction("archive", "report", "$report", host=host)

    Severity.populate(archive_mysql_abstraction_layer)
    archiver_data_source = ArchiverDataSource(archive_mysql_abstraction_layer)

    first_change = [None] * len(pv_names)
    period = ArchiveTimePeriod(data_time, delta=check_movement_for, point_count=2)
    pv_names_rbv = [f"{name}.RBV" for name in pv_names]
    for time_stamp, index, value in archiver_data_source.changes_generator(pv_names_rbv, period):
        if first_change[index] is None:
            first_change[index] = time_stamp

    values_at_data_time = archiver_data_source.initial_archiver_data_values(pv_names_rbv, data_time)

    return list(zip(pv_names, values_at_data_time, first_change))


def get_current_motor_values(pv_names):
    """
    Get the current motor values from the pvs
    Args:
        pv_names: pv names

    Returns: motor values
    """
    pv_values = {}
    for pv_name in pv_names:
        is_enabled = g.get_pv(f"{pv_name}_able", to_string=True) == "Enable"
        if not is_enabled:
            motor_name = ""
            value = 0.0
        else:
            motor_name = g.get_pv(f"{pv_name}.DESC")
            value = g.get_pv(f"{pv_name}.RBV")

        pv_values[pv_name] = (is_enabled, motor_name, value)
    return pv_values


def print_summary(archive_values, pv_values, data_time, log_file):
    """
    Print a summary of collected information
    Args:
        archive_values: values from the database
        pv_values: values from cachannel
        data_time: time data was asked for
        log_file: log file to write summary to
    """
    print_and_log(f"PVs at time {data_time}", log_file)
    print_and_log(f'{"name":12} {"motor":7}: {"archive val":12} {"diff from":12} - {"last update":19} '
                  f'{"next update":19} {"alarm":5}', log_file)
    print_and_log(f'{"":12} {"":7}: {"":12} {"current val":12} - {"(sample time)":19} '
                  f'{"(within window)":19} {"":5}', log_file)

    diff_from_current = 0.0
    for pv_name, pv_value, next_change in archive_values:
        is_enabled, motor_name, value = pv_values[pv_name]

        # value from archive db
        if pv_value.retrieval_error:
            val = f"{'archive err.':12}"
        else:
            try:
                val_as_float = float(pv_value.value)
                diff_from_current = val_as_float - value
                val = f"{val_as_float :12.3f}"
            except ValueError:
                val = f"{pv_value.value:12}"
            except TypeError:
                val = f"{'No value':12}"

        # change time
        if next_change is None:
            next_change_str = "-"
        else:
            next_change_str = next_change.strftime(DATA_TIME_DISPLAY_FORMAT)

        # sample time
        if pv_value.sample_time is None:
            last_change = "-"
        else:
            last_change = pv_value.sample_time.strftime(DATA_TIME_DISPLAY_FORMAT)

        print_and_log(f"{motor_name[:12]:12} {pv_name[-7:]}: {val} {diff_from_current:12.3f} - {last_change[:19]:19} "
                      f"{next_change_str:19} {Severity.get(pv_value.severity_id) :5}", log_file)


def define_position_as(pv_name, value, current_pos, motor_name, log_file):
    """
    Define motor position
    Args:
        pv_name: name of the motor pv
        value: value to set
        current_pos: current pv value
        log_file: log file to write message to
        motor_name: motor name/description

    """
    try:
        print_and_log(f"Defining motor position {pv_name} ({motor_name}) from {current_pos} to {value} at {datetime.now()}", log_file)
        with motor_in_set_mode(pv_name):
                g.set_pv(pv_name, value)
    except ValueError:
        print_and_log(f"Issue setting motor pv {pv_name}, please ensure it has a sensible value and that the "
                      f"calibration is set to USE", log_file)
        input("Press a key to continue")


def restore_motor_position(pv_name: str, new_position: ArchiverDataValue, next_change: datetime, is_enabled: bool,
                           motor_name: str, current_pos: Any, log_file: TextIO):
    """
    Restore the motor position after prompting the user
    Args:
        pv_name: name of the pv
        new_position: new position for the motor from teh database
        next_change: from archive what the next change of the pv was
        is_enabled: is the motor enabled
        motor_name: the name of the motor
        current_pos: the current position
        log_file: log file to write to

    """
    print()
    print()
    if not is_enabled:
        print_and_log(f"Motor not enabled: {pv_name[-7:]}", log_file)
        print()
        return
    print(f"       Motor: {motor_name} - {pv_name[-7:]}")
    print(f" Current pos: {current_pos}")
    print(f"Recorded pos: {new_position.value}  (alarm {Severity.get(new_position.severity_id):5})")
    print(f"  last moved: {new_position.sample_time}  next move {next_change}")
    while True:
        answer = input("Set motor to record position? [Y/N]")
        if answer.upper() == "Y":
            define_position_as(pv_name, new_position.value, current_pos, motor_name, log_file)
            break
        elif answer.upper() == "N":
            break
        print("Answer must be Y and N")


def summarise_and_restore_positions(data_time, prefix, controllers, host):
    """
    Summarise and restore positions for motors based on value in the archive at given time
    Args:
        data_time: time to get data for
        prefix: prefix for pvs
        controllers: motor controller ids
        host: host to get data from

    """
    pvs = []
    for controller in controllers:
        for axis in range(1, MAX_AXIS+1):
            pvs.append(f"{prefix}MOT:MTR{controller:02}{axis:02}")

    pv_values = get_current_motor_values(pvs)
    archive_values = get_archived_positions(pvs, data_time, host=host)
    with open(LOG_FILENAME, "w") as log_file:
        print(f"Log being written to {LOG_FILENAME}")
        print_summary(archive_values, pv_values, data_time, log_file)  # test pv_values and print in here

        for pv_name, pv_value, next_change in archive_values:
            is_enabled, motor_name, value = pv_values[pv_name]
            restore_motor_position(pv_name, pv_value, next_change, is_enabled, motor_name, value, log_file)
    
    for controller in controllers:
        while True:
            answer = input(f"Reset Galil controller power check for controller {controller}? [Y/N]")
            if answer.upper() == "Y":
                reset_pv = f"{prefix}MOT:DMC{controller:02}:PWRDET:RESET:SP"
                print(f"resetting {reset_pv}")
                g.set_pv(reset_pv, 1)
                break
            elif answer.upper() == "N":
                break
            print("Answer must be Y and N")



if __name__ == '__main__':
    description = "Find positions of motors in the past and restore those to current positions" \
                  "\n\nExample: restore_motor_positions.py --time 2018-01-10T09:00:00 "

    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("--host", help="(optional) Host to get data from e.g. NDXPOLREF. defaults to current instrument host name.")
    parser.add_argument("--prefix", "-p", help="(optional) PV prefix for motor controller, defaults to current instrument prefix.")
    parser.add_argument("--controller", "-c", help="(optional) Controller number, for single controller restoring."
                                                   f"defaults to restoring controllers 1-{MAX_CONTROLLER}")
    parser.add_argument("--time", "-t", help="(Required) Time to restore from iso date, 2018-12-20T16:01:02", required=True)


    args = parser.parse_args()

    data_time = parse_date_time_arg_exit_on_fail(args.time)

    # if args.host is none then this defaults to the current instrument
    g.set_instrument(args.host, import_instrument_init=False)

    if args.prefix is None:
        prefix = g.prefix_pv_name("")
    else:
        prefix = args.prefix

    if args.host is None:
        host = socket.gethostname()
    else:
        host = args.host

    if args.controller is None:
        controllers = range(1, MAX_CONTROLLER + 1)
    else:
        controllers = [int(args.controller)]

    summarise_and_restore_positions(data_time, prefix, controllers, host)
