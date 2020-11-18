# This file is part of the ISIS IBEX application.
# Copyright (C) 2017 Science & Technology Facilities Council.
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
Module for taking the configuration from the ioc data source and creating a configuration.
"""
import os

from ArchiverAccess.archive_access_configuration import ArchiveAccessConfigBuilder
from server_common.utilities import print_and_log, SEVERITY

HEADER_ANNOTATION_PREFIX = "log_header"
"""The annotation prefix for a header line, the end is the header line number"""

PV_SUB_EXPRESSION = "this_pv"
"""The pv expression to be replaced with the actual pv name"""

TRIGGER_PV = "log_trigger"
"""The annotation indicating the trigger pv"""

PERIOD_PV = "log_period_pv"
"""The annotation indicating a logging period pv"""

PERIOD_CONST_S = "log_period_seconds"
"""The annotation indicating a logging period in seconds"""

COLUMN_HEADER_ANNOTATION_PREFIX = "log_column_header"
"""The annotation prefix for a column header, the end is the column index"""

COLUMN_TEMPLATE_ANNOTATION_PREFIX = "log_column_template"
"""The annotation prefix for a column template, the end is the column index"""


class ArchiverAccessDatabaseConfigBuilder(object):
    """
    Create configurations based on the entries in the IOC database.
    """

    def __init__(self, ioc_data_source):
        """
        Constructor
        Args:
            ioc_data_source: data source for ioc data
        """
        self._ioc_data_source = ioc_data_source

    def create(self):
        """
        Create configurations from the data source
        Returns:
            list[ArchiverAccess.archive_access_configuration.ArchiveAccessConfig]: list of configuration

        """

        configurations = []
        for ioc_name, logging_items in self._ioc_data_source.get_pv_logging_info().items():
            print_and_log("Reading config for ioc: {ioc}".format(ioc=ioc_name),
                          severity=SEVERITY.INFO, src="ArchiverAccess")
            one_end_file_name_template = "{ioc_name}_{{start_time}}.dat".format(ioc_name=ioc_name)
            one_end_file_name_template = os.path.join(ioc_name, one_end_file_name_template)
            cont_file_name_template = "{ioc_name}_{{start_time}}_continuous.dat".format(ioc_name=ioc_name)
            cont_file_name_template = os.path.join(ioc_name, cont_file_name_template)
            config_builder = self._create_config_for_ioc(one_end_file_name_template, cont_file_name_template,
                                                         logging_items)

            config = config_builder.build()
            print_and_log("{0}".format(config.__rep__().replace(" - ", "\n  - ")),
                          severity=SEVERITY.INFO, src="ArchiverAccess")
            configurations.append(config)
        return configurations

    def _create_config_for_ioc(self, on_end_logging_filename_template, continuous_logging_filename_template,
                               logging_items):
        columns = {}
        all_keys = set()
        config_builder = ArchiveAccessConfigBuilder(on_end_logging_filename_template,
                                                    continuous_logging_filename_template)
        sorted_values = sorted(logging_items, key=lambda x: x[1])
        for pv_name, key, template in sorted_values:
            key_lowered = key.lower()
            if key_lowered in all_keys:
                print_and_log("Logging info key {0} is repeated.".format(key),
                              severity=SEVERITY.MAJOR, src="ArchiverAccess")
            all_keys.add(key_lowered)
            self._translate_db_annotations_to_config(key_lowered, pv_name, template, columns, config_builder)
        for column_index in sorted(columns.keys()):
            column_header, column_template = columns[column_index]
            config_builder.table_column(column_header, column_template)
        return config_builder

    def _translate_db_annotations_to_config(self, key, pv_name, template, columns, config_builder):
        value = template.replace(PV_SUB_EXPRESSION, pv_name)
        if key.startswith(HEADER_ANNOTATION_PREFIX):
            config_builder.header(value)
        elif key == TRIGGER_PV:
            config_builder.trigger_pv(self._use_default_if_blank(value, pv_name))
        elif key == PERIOD_PV:
            config_builder.logging_period_pv(self._use_default_if_blank(value, pv_name))
        elif key == PERIOD_CONST_S:
            try:
                config_builder.logging_period_seconds(float(value))
            except (TypeError, ValueError):
                print_and_log("Invalid logging period set '{0}'".format(value),
                              severity=SEVERITY.MAJOR, src="ArchiverAccess")
        elif key.startswith(COLUMN_HEADER_ANNOTATION_PREFIX):
            default_template = "{{{pv_name}}}".format(pv_name=pv_name)
            index = key[len(COLUMN_HEADER_ANNOTATION_PREFIX):]
            current_header, current_template = columns.get(index, (None, default_template))
            columns[index] = (value, current_template)

        elif key.startswith(COLUMN_TEMPLATE_ANNOTATION_PREFIX):
            default_header = self._use_default_if_blank(value, pv_name)
            index = key[len(COLUMN_TEMPLATE_ANNOTATION_PREFIX):]
            current_header, current_template = columns.get(index, (default_header, None))

            pv_name_template = "{{{pv_name}}}".format(pv_name=pv_name)
            columns[index] = (current_header, self._use_default_if_blank(value, pv_name_template))

    def _use_default_if_blank(self, value, default):
        if value is None or value == "":
            return default
        return value
