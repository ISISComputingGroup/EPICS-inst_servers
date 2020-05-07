"""
Reflectometry pv manager
"""
import logging

from enum import Enum
from pcaspy import Severity

import ReflectometryServer
from ReflectometryServer.server_status_manager import STATUS, STATUS_MANAGER, ProblemInfo
from ReflectometryServer.footprint_manager import FP_SP_KEY, FP_SP_RBV_KEY, FP_RBV_KEY
from pcaspy.alarm import SeverityStrings
from ReflectometryServer.parameters import BeamlineParameterType
from server_common.ioc_data_source import PV_INFO_FIELD_NAME, PV_DESCRIPTION_NAME
from server_common.utilities import create_pv_name, remove_from_end, print_and_log, SEVERITY, compress_and_hex
import json
from collections import OrderedDict

logger = logging.getLogger(__name__)

MAX_ALARM_ID = 15

# PCASpy Enum PVs are limited to 14 items
AlarmStringsTruncated = [
    "NO_ALARM",
    "READ",
    "WRITE",
    "HIHI",
    "HIGH",
    "LOLO",
    "LOW",
    "STATE",
    "COS",
    "COMM",
    "TIMEOUT",
    "HWLIMIT",
    "CALC",
    "SCAN",
    "LINK",
    "OTHER",
    # "SOFT",
    # "BAD_SUB",
    # "UDF",
    # "DISABLE",
    # "SIMM",
    # "READ_ACCESS",
    # "WRITE_ACCESS"
]

PARAM_PREFIX = "PARAM"
BEAMLINE_PREFIX = "BL:"
SERVER_STATUS = "STAT"
SERVER_MESSAGE = "MSG"
SERVER_ERROR_LOG = "LOG"
BEAMLINE_MODE = BEAMLINE_PREFIX + "MODE"
BEAMLINE_MOVE = BEAMLINE_PREFIX + "MOVE"
PARAM_INFO = "PARAM_INFO"
DRIVER_INFO = "DRIVER_INFO"
BEAMLINE_CONSTANT_INFO = "CONST_INFO"
ALIGN_INFO = "ALIGN_INFO"
IN_MODE_SUFFIX = ":IN_MODE"
SP_SUFFIX = ":SP"
SP_RBV_SUFFIX = ":SP:RBV"
ACTION_SUFFIX = ":ACTION"
SET_AND_NO_ACTION_SUFFIX = ":SP_NO_ACTION"
RBV_AT_SP = ":RBV:AT_SP"
CHANGING = ":CHANGING"
CHANGED_SUFFIX = ":CHANGED"
DEFINE_POSITION_AS = ":DEFINE_POSITION_AS"
CONST_PREFIX = "CONST"

VAL_FIELD = ".VAL"
STAT_FIELD = ".STAT"
SEVR_FIELD = ".SEVR"
DESC_FIELD = ".DESC"

FOOTPRINT_PREFIX = "FP"
SAMPLE_LENGTH = "{}:{}".format(FOOTPRINT_PREFIX, "SAMPLE_LENGTH")
FP_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "FOOTPRINT")
DQQ_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "DQQ")
QMIN_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "QMIN")
QMAX_TEMPLATE = "{}:{{}}:{}".format(FOOTPRINT_PREFIX, "QMAX")
FOOTPRINT_PREFIXES = [FP_SP_KEY, FP_SP_RBV_KEY, FP_RBV_KEY]

PARAM_FIELDS_BINARY = {'type': 'enum', 'enums': ["NO", "YES"]}
PARAM_IN_MODE = {'type': 'enum', 'enums': ["NO", "YES"]}
PARAM_FIELDS_ACTION = {'type': 'int', 'count': 1, 'value': 0}
OUT_IN_ENUM_TEXT = ["OUT", "IN"]
STANDARD_FLOAT_PV_FIELDS = {'type': 'float', 'prec': 3, 'value': 0.0}
STANDARD_2048_CHAR_WF_FIELDS = {'type': 'char', 'count': 2048, 'value': ""}
ALARM_STAT_PV_FIELDS = {'type': 'enum', 'enums': AlarmStringsTruncated}
ALARM_SEVR_PV_FIELDS = {'type': 'enum', 'enums': SeverityStrings}

PARAMS_FIELDS_BEAMLINE_TYPES = {
    BeamlineParameterType.IN_OUT: {'type': 'enum', 'enums': OUT_IN_ENUM_TEXT},
    BeamlineParameterType.FLOAT: STANDARD_FLOAT_PV_FIELDS}


def convert_to_epics_pv_value(parameter_type, value):
    """
    Convert from parameter value to the epic pv value
    Args:
        parameter_type (BeamlineParameterType): parameters type
        value: value to convert

    Returns: epics value

    """
    if parameter_type == BeamlineParameterType.IN_OUT:
        if value:
            return OUT_IN_ENUM_TEXT.index("IN")
        else:
            return OUT_IN_ENUM_TEXT.index("OUT")
    else:
        if value is None:
            return float("NaN")
        else:
            return value


def convert_from_epics_pv_value(parameter_type, value):
    """
    Convert from epic pv value to the parameter value
    Args:
        parameter_type (BeamlineParameterType): parameters type
        value: value to convert

    Returns: epics value

    """
    if parameter_type == BeamlineParameterType.IN_OUT:
        return value == OUT_IN_ENUM_TEXT.index("IN")
    else:
        return value


def is_pv_name_this_field(field_name, pv_name):
    """
    Args:
        field_name: field name to match
        pv_name: pv name to match

    Returns: True if field name is pv name (with oe without VAL  field)

    """
    pv_name_no_val = remove_from_end(pv_name, VAL_FIELD)
    return pv_name_no_val == field_name


class PvSort(Enum):
    """
    Enum for the type of PV
    """
    RBV = 0
    ACTION = 1
    SP_RBV = 2
    SP = 3
    SET_AND_NO_ACTION = 4
    CHANGED = 6
    IN_MODE = 7
    CHANGING = 8
    RBV_AT_SP = 9
    DEFINE_POS_AS = 10

    @staticmethod
    def what(pv_sort):
        """
        Args:
            pv_sort: pv sort to determine

        Returns: what the pv sort does
        """
        if pv_sort == PvSort.RBV:
            return ""
        elif pv_sort == PvSort.ACTION:
            return "(Do the action)"
        elif pv_sort == PvSort.SP_RBV:
            return "(Set point readback)"
        elif pv_sort == PvSort.SP:
            return "(Set point)"
        elif pv_sort == PvSort.SET_AND_NO_ACTION:
            return "(Set point with no action executed)"
        elif pv_sort == PvSort.CHANGED:
            return "(Is changed)"
        elif pv_sort == PvSort.IN_MODE:
            return "(Is in mode)"
        elif pv_sort == PvSort.CHANGING:
            return "(Is changing)"
        elif pv_sort == PvSort.RBV_AT_SP:
            return "(Tolerance between RBV and target set point)"
        elif pv_sort == PvSort.DEFINE_POS_AS:
            return "(Define the value of current position)"
        else:
            print_and_log("Unknown pv sort!! {}".format(pv_sort), severity=SEVERITY.MAJOR, src="REFL")
            return "(unknown)"

    def get_from_parameter(self, parameter):
        """
        Get the value of the correct sort from a parameter
        Args:
            parameter(ReflectometryServer.parameters.BeamlineParameter): the parameter to get the value from

        Returns: the value of the parameter of the correct sort
        """
        if self == PvSort.SP:
            return convert_to_epics_pv_value(parameter.parameter_type, parameter.sp)
        elif self == PvSort.SP_RBV:
            return convert_to_epics_pv_value(parameter.parameter_type, parameter.sp_rbv)
        elif self == PvSort.RBV:
            return convert_to_epics_pv_value(parameter.parameter_type, parameter.rbv)
        elif self == PvSort.SET_AND_NO_ACTION:
            return convert_to_epics_pv_value(parameter.parameter_type, parameter.sp_no_move)
        elif self == PvSort.CHANGED:
            return parameter.sp_changed
        elif self == PvSort.ACTION:
            return parameter.move
        elif self == PvSort.CHANGING:
            return parameter.is_changing
        elif self == PvSort.RBV_AT_SP:
            return parameter.rbv_at_sp
        elif self == PvSort.DEFINE_POS_AS:
            if parameter.define_current_value_as is None:
                return float("NaN")
            return parameter.define_current_value_as.new_value
        return float("NaN")

    def get_parameter_alarm(self, parameter):
        """
        Get the alarm status of this parameter. Only applicable for Readback PVs.

        Args:
            parameter(ReflectometryServer.parameters.BeamlineParameter): the parameter to get the value from

        Returns: the alarm severity and status of this parameter.
        """
        if self == PvSort.RBV:
            return parameter.alarm_severity, parameter.alarm_status
        else:
            return None, None


class PVManager:
    """
    Holds reflectometry PVs and associated utilities.
    """
    def __init__(self):
        """
        The constructor.
        """
        self._beamline = None  # type: ReflectometryServer.beamline.Beamline
        self.PVDB = {}
        self.initial_PVs = []
        self._params_pv_lookup = OrderedDict()
        self._footprint_parameters = {}
        self._add_status_pvs()

        for pv_name in self.PVDB.keys():
            logger.info("Creating pv: {}".format(pv_name))

    def _add_status_pvs(self):
        """
        PVs for server status
        """
        status_fields = {'type': 'enum',
                         'enums': [code.display_string for code in STATUS.status_codes()],
                         'states': [code.alarm_severity for code in STATUS.status_codes()]}
        self._add_pv_with_fields(SERVER_STATUS, None, status_fields, "Status of the beam line", PvSort.RBV,
                                 archive=True, interest="HIGH", alarm=True, on_init=True)
        self._add_pv_with_fields(SERVER_MESSAGE, None, {'type': 'char', 'count': 400}, "Message about the beamline",
                                 PvSort.RBV, archive=True, interest="HIGH", on_init=True)
        self._add_pv_with_fields(SERVER_ERROR_LOG, None, {'type': 'char', 'count': 10000},
                                 "Error log for the Reflectometry Server", PvSort.RBV, archive=True, interest="HIGH",
                                 on_init=True)

    def set_beamline(self, beamline):
        """
        Set the beamline for the manager and add needed pvs

        Args:
            beamline (ReflectometryServer.beamline.Beamline): beamline to set

        """
        self._beamline = beamline

        self._add_global_pvs()
        self._add_footprint_calculator_pvs()
        self._add_all_parameter_pvs()
        self._add_all_driver_pvs()
        self._add_constants_pvs()

        for pv_name in [pv for pv in self.PVDB.keys() if pv not in self.initial_PVs]:
            logger.info("Creating pv: {}".format(pv_name))

    def _add_global_pvs(self):
        """
        Add PVs that affect the whole of the reflectometry system to the server's PV database.

        """
        self._add_pv_with_fields(BEAMLINE_MOVE, None, PARAM_FIELDS_ACTION, "Move the beam line", PvSort.RBV,
                                 archive=True, interest="HIGH")
        # PVs for mode
        mode_fields = {'type': 'enum', 'enums': self._beamline.mode_names}
        self._add_pv_with_fields(BEAMLINE_MODE, None, mode_fields, "Beamline mode", PvSort.RBV, archive=True,
                                 interest="HIGH")
        self._add_pv_with_fields(BEAMLINE_MODE + SP_SUFFIX, None, mode_fields, "Beamline mode", PvSort.SP)

    def _add_footprint_calculator_pvs(self):
        """
        Add PVs related to the footprint calculation to the server's PV database.
        """
        self._add_pv_with_fields(SAMPLE_LENGTH, None, STANDARD_FLOAT_PV_FIELDS,
                                 "Sample Length", PvSort.SP_RBV, archive=True, interest="HIGH")

        for prefix in FOOTPRINT_PREFIXES:
            for template, description in [(FP_TEMPLATE, "Beam Footprint"),
                                          (DQQ_TEMPLATE, "Beam Resolution dQ/Q"),
                                          (QMIN_TEMPLATE, "Minimum measurable Q with current setup"),
                                          (QMAX_TEMPLATE, "Maximum measurable Q with current setup")]:
                self._add_pv_with_fields(template.format(prefix), None,
                                         STANDARD_FLOAT_PV_FIELDS,
                                         description, PvSort.RBV, archive=True, interest="HIGH")

    def _add_all_parameter_pvs(self):
        """
        Add PVs for each beamline parameter in the reflectometry configuration to the server's PV database.
        """
        param_info = []
        align_info = []
        for parameter in self._beamline.parameters.values():
            param_info_record = self._add_parameter_pvs(parameter)
            param_info.append(param_info_record)
            if parameter.define_current_value_as is not None:
                align_info_record = {
                    "name": param_info_record["name"],
                    "prepended_alias": param_info_record["prepended_alias"],
                    "type": "align"
                }
                align_info.append(align_info_record)

        self._add_pv_with_fields(PARAM_INFO, None, STANDARD_2048_CHAR_WF_FIELDS, "All parameters information",
                                 None, value=compress_and_hex(json.dumps(param_info)))

        self._add_pv_with_fields(ALIGN_INFO, None, STANDARD_2048_CHAR_WF_FIELDS, "All alignment pvs information",
                                 None, value=compress_and_hex(json.dumps(align_info)))

    def _add_parameter_pvs(self, parameter):
        """
        Adds all PVs needed for one beamline parameter to the PV database.

        Args:
            parameter (ReflectometryServer.parameters.BeamlineParameter): the beamline parameter

        Returns:
            parameter information
        """
        try:
            param_name = parameter.name
            description = parameter.description
            param_alias = create_pv_name(param_name, self.PVDB.keys(), PARAM_PREFIX, limit=10)
            prepended_alias = "{}:{}".format(PARAM_PREFIX, param_alias)

            parameter_type = parameter.parameter_type
            fields = PARAMS_FIELDS_BEAMLINE_TYPES[parameter_type]

            # Readback PV
            self._add_pv_with_fields(prepended_alias, param_name, fields, description, PvSort.RBV, archive=True,
                                     interest="HIGH")

            # Setpoint PV
            self._add_pv_with_fields(prepended_alias + SP_SUFFIX, param_name, fields, description, PvSort.SP,
                                     archive=True)

            # Setpoint readback PV
            self._add_pv_with_fields(prepended_alias + SP_RBV_SUFFIX, param_name, fields, description, PvSort.SP_RBV)

            # Set value and do not action PV
            self._add_pv_with_fields(prepended_alias + SET_AND_NO_ACTION_SUFFIX, param_name, fields, description,
                                     PvSort.SET_AND_NO_ACTION)

            # Changed PV
            self._add_pv_with_fields(prepended_alias + CHANGED_SUFFIX, param_name, PARAM_FIELDS_BINARY, description,
                                     PvSort.CHANGED)

            # Action PV
            self._add_pv_with_fields(prepended_alias + ACTION_SUFFIX, param_name, PARAM_FIELDS_ACTION, description,
                                     PvSort.ACTION)

            # Moving state PV
            self._add_pv_with_fields(prepended_alias + CHANGING, param_name, PARAM_FIELDS_BINARY, description,
                                     PvSort.CHANGING)

            # In mode PV
            self._add_pv_with_fields(prepended_alias + IN_MODE_SUFFIX, param_name, PARAM_IN_MODE, description,
                                     PvSort.IN_MODE)

            # RBV to SP:RBV tolerance
            self._add_pv_with_fields(prepended_alias + RBV_AT_SP, param_name, PARAM_FIELDS_BINARY, description,
                                     PvSort.RBV_AT_SP)

            # define position at
            if parameter.define_current_value_as is not None:
                align_fields = STANDARD_FLOAT_PV_FIELDS.copy()
                align_fields["asg"] = "MANAGER"
                self._add_pv_with_fields(prepended_alias + DEFINE_POSITION_AS, param_name, align_fields, description,
                                         PvSort.DEFINE_POS_AS)

            return {"name": param_name,
                    "prepended_alias": prepended_alias,
                    "type": BeamlineParameterType.name_for_param_list(parameter_type)}

        except Exception as err:
            STATUS_MANAGER.update_error_log("Error adding PV for parameter {}: {}".format(parameter.name, err.message))
            STATUS_MANAGER.update_active_problems(
                ProblemInfo("Error adding parameter PV", parameter.name, Severity.MAJOR_ALARM))

    def _add_pv_with_fields(self, pv_name, param_name, pv_fields, description, sort, archive=False, interest=None,
                            alarm=False, value=None, on_init=False):
        """
        Add param to pv list with .val and correct fields and to parm look up
        Args:
            pv_name: name of the pv
            param_name: name of the parameter; None for not a parameter
            pv_fields: pv fields to use
            description: description of the pv for .DESC field
            sort: sort of pv it is
            archive: True if it should be archived
            interest: level of interest; None is not interesting
            alarm: True if this pv represents the alarm state of the IOC; false otherwise

        Returns:

        """
        pv_fields = pv_fields.copy()
        if sort is None:
            pv_fields[PV_DESCRIPTION_NAME] = description
        else:
            pv_fields[PV_DESCRIPTION_NAME] = description + PvSort.what(sort)

        if value is not None:
            pv_fields["value"] = value

        pv_fields_mod = pv_fields.copy()
        pv_fields_mod[PV_INFO_FIELD_NAME] = {}
        if interest is not None:
            pv_fields_mod[PV_INFO_FIELD_NAME]["INTEREST"] = interest
        if archive:
            pv_fields_mod[PV_INFO_FIELD_NAME]["archive"] = "VAL"
        if alarm:
            pv_fields_mod[PV_INFO_FIELD_NAME]["alarm"] = "Reflectometry IOC (REFL)"

        self.PVDB[pv_name] = pv_fields_mod
        self.PVDB[pv_name + VAL_FIELD] = pv_fields
        self.PVDB[pv_name + DESC_FIELD] = {'type': 'string', 'value': pv_fields[PV_DESCRIPTION_NAME]}
        self.PVDB[pv_name + STAT_FIELD] = ALARM_STAT_PV_FIELDS.copy()
        self.PVDB[pv_name + SEVR_FIELD] = ALARM_SEVR_PV_FIELDS.copy()

        if param_name is not None:
            self._params_pv_lookup[pv_name] = (param_name, sort)

        if on_init:
            self.initial_PVs.append(pv_name)
            self.initial_PVs.append(pv_name + VAL_FIELD)
            self.initial_PVs.append(pv_name + STAT_FIELD)
            self.initial_PVs.append(pv_name + SEVR_FIELD)

    def get_init_filtered_pvdb(self):
        """

        Returns:
            pvs that were created after beamline was set.

        """
        return {key: value for key, value in self.PVDB.iteritems() if key not in self.initial_PVs}

    def _add_all_driver_pvs(self):
        """
        Add all pvs for the drivers.
        """
        self.drivers_pv = {}
        driver_info = []
        for driver in self._beamline.drivers:
            if driver.has_engineering_correction:
                correction_alias = create_pv_name(driver.name, self.PVDB.keys(), "COR", limit=12, allow_colon=True)
                prepended_alias = "{}:{}".format("COR", correction_alias)

                self._add_pv_with_fields(prepended_alias, None, STANDARD_FLOAT_PV_FIELDS, "Engineering Correction",
                                         None, archive=True)
                self._add_pv_with_fields("{}:DESC".format(prepended_alias), None, STANDARD_2048_CHAR_WF_FIELDS,
                                         "Engineering Correction Full Description", None)

                self.drivers_pv[driver] = prepended_alias

                driver_info.append({"name": driver.name, "prepended_alias": prepended_alias})

        self._add_pv_with_fields(DRIVER_INFO, None, STANDARD_2048_CHAR_WF_FIELDS, "All corrections information",
                                 None, value=compress_and_hex(json.dumps(driver_info)))

    def _add_constants_pvs(self):
        """
        Add pvs for the beamline constants
        """
        beamline_constant_info = []

        for beamline_constant in self._beamline.beamline_constants:
            const_alias = create_pv_name(beamline_constant.name, self.PVDB.keys(), CONST_PREFIX,
                                         limit=20, allow_colon=True)
            prepended_alias = "{}:{}".format(CONST_PREFIX, const_alias)

            if isinstance(beamline_constant.value, bool):
                value = 1 if bool(beamline_constant.value) else 0
                fields = PARAM_FIELDS_BINARY
            else:
                value = float(beamline_constant.value)
                fields = STANDARD_FLOAT_PV_FIELDS

            self._add_pv_with_fields(prepended_alias, None, fields, beamline_constant.description, None,
                                     archive=True, interest="MEDIUM", value=value)
            beamline_constant_info.append(
                {"name": beamline_constant.name, "prepended_alias": prepended_alias, "type": "float_value"})

        self._add_pv_with_fields(BEAMLINE_CONSTANT_INFO, None, STANDARD_2048_CHAR_WF_FIELDS, "All value parameters", None,
                                 value=compress_and_hex(json.dumps(beamline_constant_info)))

    def param_names_pv_names_and_sort(self):
        """

        Returns:
            (list[str, tuple[str, PvSort]]): The list of PVs of all beamline parameters.

        """
        return self._params_pv_lookup.items()

    def is_param(self, pv_name):
        """

        Args:
            pv_name: name of the pv

        Returns:
            True if the pv is a pv for beamline parameter
        """
        return remove_from_end(pv_name, VAL_FIELD) in self._params_pv_lookup

    def get_param_name_and_sort_from_pv(self, pv_name):
        """
        Args:
            pv_name: name of pv to find

        Returns:
            (str, PvSort): parameter name and sort for the given pv
        """
        return self._params_pv_lookup[self.strip_fields_from_pv(pv_name)]

    def strip_fields_from_pv(self, pv_name):
        """
        Remove suffixes for fields from the end of a given PV.

        Args:
            pv_name: name of the pv

        Returns: The PV name with any of the known field suffixes stripped off the end.
        """
        for field in [VAL_FIELD, STAT_FIELD, SEVR_FIELD]:
            pv_name = remove_from_end(pv_name, field)
        return pv_name

    @staticmethod
    def is_beamline_mode(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline mode pv
        """
        pv_name_no_val = remove_from_end(pv_name, VAL_FIELD)
        return pv_name_no_val == BEAMLINE_MODE or pv_name_no_val == BEAMLINE_MODE + SP_SUFFIX

    @staticmethod
    def is_beamline_move(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the beamline move pv
        """
        return is_pv_name_this_field(BEAMLINE_MOVE, pv_name)

    @staticmethod
    def is_sample_length(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the sample length pv
        """
        return is_pv_name_this_field(SAMPLE_LENGTH, pv_name)

    @staticmethod
    def is_server_status(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the server status pv
        """
        return is_pv_name_this_field(SERVER_STATUS, pv_name)

    @staticmethod
    def is_server_message(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the server message pv
        """
        return is_pv_name_this_field(SERVER_MESSAGE, pv_name)

    @staticmethod
    def is_error_log(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this the server error log pv
        """
        return is_pv_name_this_field(SERVER_ERROR_LOG, pv_name)

    @staticmethod
    def is_alarm_status(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this is an alarm status pv
        """
        return pv_name.endswith(STAT_FIELD)

    @staticmethod
    def is_alarm_severity(pv_name):
        """
        Args:
            pv_name: name of the pv

        Returns: True if this is an alarm severity pv
        """
        return pv_name.endswith(SEVR_FIELD)
