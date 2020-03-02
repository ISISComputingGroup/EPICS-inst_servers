import logging
from collections import namedtuple

from enum import Enum
from pcaspy import Severity

from server_common.observable import observable

StatusDescription = namedtuple("StatusDescription", [
    'display_string',   # A string representation of the server state
    'alarm_severity'])  # The alarm severity associated to this state, represented as an int (see Channel Access doc)

StatusUpdate = namedtuple("StatusUpdate", [
    'server_status',    # The server status
    'server_message'])  # The server status display message

ProblemInfo = namedtuple("ProblemDescription", [
    'description',      # The problem description
    'source',           # The problem source
    'severity'])        # The severity of the problem

ActiveProblemsUpdate = namedtuple("ActiveProblemsUpdate", [
    'errors',           # Dictionary of errors (description:sources)
    'warnings',         # Dictionary of warnings (description:sources)
    'other'])           # Dictionary of other problems (description:sources)

ErrorLogUpdate = namedtuple("ErrorLogUpdate", [
    'errors'])          # The current error log as a list of strings


logger = logging.getLogger(__name__)


class PROBLEMS(Enum):
    PARAMETER_NOT_INITIALISED = "Parameter not initialised"


class STATUS(Enum):
    """
    Beamline States.
    """
    INITIALISING = StatusDescription("INITIALISING", Severity.MINOR_ALARM)
    OKAY = StatusDescription("OKAY", Severity.NO_ALARM)
    WARNING = StatusDescription("WARNING", Severity.MINOR_ALARM)
    ERROR = StatusDescription("ERROR", Severity.MAJOR_ALARM)
    UNKNOWN = StatusDescription("UNKNOWN", Severity.INVALID_ALARM)

    @staticmethod
    def status_codes():
        """
        Returns:
            (list[str]) status codes for the beamline
        """
        # noinspection PyTypeChecker
        return [status.value for status in STATUS]

    @property
    def display_string(self):
        """
        Returns: display string for the enum
        """
        return self.value.display_string

    @property
    def alarm_severity(self):
        """
        Returns: Alarm severity of beamline status
        """
        return self.value.alarm_severity


@observable(StatusUpdate, ActiveProblemsUpdate, ErrorLogUpdate)
class _ServerStatusManager(object):
    """
    Handler for setting the status of the reflectometry server.
    """
    INITIALISING_MESSAGE = "Reflectometry Server is initialising. Check configurations is correct and all motor IOCs " \
                           "are running if this is taking longer than expected."

    def __init__(self):
        self._status = STATUS.OKAY
        self._message = ""
        self._initialising = True

        self.active_errors = {}
        self.active_warnings = {}
        self.active_other_problems = {}

        self.error_log = []

    def set_initialised(self):
        self._initialising = False
        self._trigger_status_update()

    def clear_all(self):
        self._clear_status()
        self._clear_problems()
        self._clear_log()

    def _clear_status(self):
        self._status = STATUS.OKAY
        self._message = ""
        self._trigger_status_update()

    def _clear_problems(self):
        self.active_errors = {}
        self.active_warnings = {}
        self.active_other_problems = {}
        self._update_status()
        self.trigger_listeners(self._get_active_problems_update())

    def _clear_log(self):
        self.error_log = []
        self.trigger_listeners(ErrorLogUpdate(self.error_log))

    def _get_problems_by_severity(self, severity):
        if severity is Severity.MAJOR_ALARM:
            return self.active_errors
        elif severity is Severity.MINOR_ALARM:
            return self.active_warnings
        else:
            return self.active_other_problems

    def _get_highest_error_level(self):
        if self.active_errors:
            return STATUS.ERROR
        elif self.active_warnings:
            return STATUS.WARNING
        elif self.active_other_problems:
            return STATUS.UNKNOWN
        else:
            return STATUS.OKAY

    def _get_active_problems_update(self):
        return ActiveProblemsUpdate(self.active_errors, self.active_warnings, self.active_other_problems)

    def _update_status(self):
        """
        Update the server status and display message and notifies listeners.

        Params:
            status (StatusDescription): The updated beamline status
            message (String): The updated beamline status display message
        """
        self._status = self._get_highest_error_level()
        self._trigger_status_update()

    def _trigger_status_update(self):
        self.trigger_listeners(StatusUpdate(self._status, self._message))

    def update_active_problems(self, problem):
        """
        Updates the active problems known to the status manager. If the problem is already known, it just appends the
        new source.

        Params:
            problem(ProblemInfo): The problem to add
        """
        dict_to_append = self._get_problems_by_severity(problem.severity)
        if problem.description in self.active_errors.keys():
            dict_to_append[problem.description].add(problem.source)
        else:
            dict_to_append[problem.description] = {problem.source}

        self.message = self._construct_status_message()
        self.status = self._get_highest_error_level()

        self.trigger_listeners(self._get_active_problems_update())

    def update_error_log(self, message):
        """
        Logs an error and appends it to the list of current errors for display to the user.

        Params:
            message(string): The log message to append
        """
        logger.error(message)
        self.error_log.append(message)
        self.trigger_listeners(ErrorLogUpdate(self.error_log))

    @property
    def status(self):
        if self._initialising:
            return STATUS.INITIALISING
        else:
            return self._status

    @status.setter
    def status(self, status_to_set):
        self._status = status_to_set
        self._trigger_status_update()

    @property
    def message(self):
        if self._initialising:
            return self.INITIALISING_MESSAGE
        else:
            return self._message

    @message.setter
    def message(self, message_to_set):
        self._message = message_to_set
        self._trigger_status_update()

    def _construct_status_message(self):
        message = ""
        if self.active_errors:
            message += "Errors:\n"
            for description, sources in self.active_errors.items():
                message += "\t{}".format(self._format_entry(description, sources))
        if self.active_warnings:
            message += "Warnings:\n"
            for description, sources in self.active_warnings.items():
                message += "\t{}".format(self._format_entry(description, sources))
        if self.active_other_problems:
            message += "Other issues:\n"
            for description, sources in self.active_other_problems.items():
                message += "\t{}".format(self._format_entry(description, sources))

        print(message)
        return message

    def _format_entry(self, description, sources):
        return "{} ({})\n".format(description, len(sources))


STATUS_MANAGER = _ServerStatusManager()