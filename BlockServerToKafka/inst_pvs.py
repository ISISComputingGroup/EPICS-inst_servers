from threading import Timer

from genie_python.mysql_abstraction_layer import SQLAbstraction
from server_common.utilities import print_and_log

from BlockServerToKafka.kafka_producer import ProducerWrapper

UPDATE_FREQUENCY_S = 30.0


class InstPVs(object):
    def __init__(
        self, producer: ProducerWrapper, sql_abstraction: SQLAbstraction | None = None
    ) -> None:
        self._pvs: set[str] = set()
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

        job = Timer(UPDATE_FREQUENCY_S, action)
        job.start()

    def update_pvs_from_mysql(self) -> None:
        rows = self._sql.query('SELECT pvname, value FROM iocdb.pvinfo WHERE infoname="archive";')
        if rows is None:
            return

        pvs = set()
        for row in rows:
            basename, fields = row
            assert isinstance(fields, str)
            for field in fields.split():
                if all(c in "0123456789." for c in field):
                    # This is an archiving time period, e.g. the 5.0 in
                    # info(archive, "5.0 VAL")
                    # Ignore it
                    continue
                pvs.add(f"{basename}.{field}")

        if self._pvs != pvs:
            print_and_log(f"Inst configuration changed to: {pvs}")
            self.producer.remove_config(list(self._pvs - pvs))
            self.producer.add_config(list(pvs - self._pvs))
            self._pvs = pvs
