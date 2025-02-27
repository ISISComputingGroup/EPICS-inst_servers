from __future__ import absolute_import, division, print_function, unicode_literals


class MockProcServWrapper(object):
    """
    Mock ProcServer
    """

    def __init__(self) -> None:
        self.ps_status = dict()
        self.ps_status["simple1"] = "SHUTDOWN"
        self.ps_status["simple2"] = "SHUTDOWN"
        self.ps_status["testioc"] = "SHUTDOWN"
        self.ps_status["stopdioc"] = "SHUTDOWN"

    @staticmethod
    def generate_prefix(prefix: str, ioc: str) -> str:
        return f"{prefix}CS:PS:{ioc}"

    def start_ioc(self, prefix: str, ioc: str) -> None:
        self.ps_status[ioc.lower()] = "RUNNING"

    def stop_ioc(self, prefix: str, ioc: str) -> None:
        """Stops the specified IOC"""
        self.ps_status[ioc.lower()] = "SHUTDOWN"

    def restart_ioc(self, prefix: str, ioc: str) -> None:
        self.ps_status[ioc.lower()] = "RUNNING"

    def get_ioc_status(self, prefix: str, ioc: str) -> str:
        if ioc.lower() not in self.ps_status.keys():
            raise TimeoutError("Could not find IOC (%s)" % self.generate_prefix(prefix, ioc))
        else:
            return self.ps_status[ioc.lower()]

    def ioc_exists(self, prefix: str, ioc: str) -> bool:
        try:
            self.get_ioc_status(prefix, ioc)
            return True
        except TimeoutError:
            return False
