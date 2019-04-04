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
"""
Script for generating a log file from the archive.
"""
import argparse
from datetime import datetime, timedelta

import os
import sys

try:
    from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    from ArchiverAccess.archive_data_file_creator import ArchiveDataFileCreator
from ArchiverAccess.archive_time_period import ArchiveTimePeriod
from ArchiverAccess.archiver_data_source import ArchiverDataSource
from ArchiverAccess.archive_access_configuration import ArchiveAccessConfigBuilder
from server_common.mysql_abstraction_layer import SQLAbstraction

finish = False
"""Finish the program"""


def not_readonly(path):
    """
    Final function of the log
    Args:
        path: path of file

    """
    print("Created log file {}".format(path))


def create_log(pv_values, time_period, filename, host="127.0.0.1"):
    """
    Create pv monitors based on the iocdatabase

    Returns: monitor for PV

    """
    archive_mysql_abstraction_layer = SQLAbstraction("archive", "report", "$report", host=host)
    archiver_data_source = ArchiverDataSource(archive_mysql_abstraction_layer)

    with open(filename, "w") as log_file:
        log_file.write("Initial values\n")
        for pv_name, val in zip(pv_values, archiver_data_source.initial_values(pv_values, time_period.start_time)):
            log_file.write("{}, {}\n".format(pv_name, val))

        for time_stamp, index, value in archiver_data_source.changes_generator(pv_values, time_period):
            time_stamp_as_str = time_stamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
            log_file.write("{}, {}, {}\n".format(time_stamp_as_str, pv_values[index], value))


if __name__ == '__main__':
    description = "Create a log of events from the archive. E.g. python log_event_generator.py " \
                  "--start_time 2018-01-10T09:00:00 --point_count 1000 --delta_time 1 --host ndximat " \
                  "--filename.csv  " \
                  "IN:IMAT:MOT:MTR0101.RBV IN:IMAT:MOT:MTR0102.RBV"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--point_count", "-c", type=int, help="Number of sample points", required=True)
    parser.add_argument("--start_time", "-s", help="Start time for sample iso date, 2018-12-20T16:01:02", required=True)
    parser.add_argument("--delta_time", "-d", type=float, help="The time between points in seconds", required=True)
    parser.add_argument("--host", default="localhost", help="Host to get data from defaults to localhost")
    parser.add_argument("--filename", "-f", default="log.log",
                        help="Filename to use for the log file.")
    parser.add_argument("--default_field", default="VAL",
                        help="If the pv has no field add this field to it.")

    parser.add_argument("pv_values", nargs="+",
                        help="Each pv appearing in the data")

    args = parser.parse_args()

    try:
        data_start_time = datetime.strptime(args.start_time, "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError) as ex:
        print("Can not interpret date '{}' error: {}".format(args.start_time, ex))
        exit(1)

    the_time_period = ArchiveTimePeriod(data_start_time, timedelta(seconds=args.delta_time), args.point_count)

    create_log(args.pv_values, the_time_period, filename=args.filename, host=args.host)
