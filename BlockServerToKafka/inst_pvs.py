from threading import Timer

from genie_python.mysql_abstraction_layer import SQLAbstraction
from server_common.utilities import print_and_log

from BlockServerToKafka.kafka_producer import ProducerWrapper


class InstPVs(object):
    def __init__(
        self, producer: ProducerWrapper, sql_abstraction: SQLAbstraction | None = None
    ) -> None:
        self._pvs = []
        self._sql = (
            SQLAbstraction(dbid="iocdb", user="report", password="$report", host="localhost")
            if sql_abstraction is None
            else sql_abstraction
        )
        self.producer = producer

    def schedule(self) -> None:
        def action() -> None:
            self.update_pvs_from_mysql()
            self.schedule()

        job = Timer(30.0, action)
        job.start()

    def update_pvs_from_mysql(self) -> None:
        pvs = self._sql.query('SELECT pvname FROM iocdb.pvinfo WHERE infoname="archive";')
        if pvs is None:
            return

        pvs = [pv[0] for pv in pvs]

        if set(self._pvs) != set(pvs):
            print_and_log(f"Inst configuration changed to: {pvs}")
            self.producer.remove_config(self._pvs)
            self.producer.add_config(pvs)
            self._pvs = pvs
