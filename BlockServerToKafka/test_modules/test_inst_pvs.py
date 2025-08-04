import unittest
from unittest.mock import MagicMock, patch

from BlockServerToKafka.inst_pvs import InstPVs


class TestInstPVs(unittest.TestCase):
    def test_calling_start_schedules_timer(self):
        with patch("BlockServerToKafka.inst_pvs.Timer") as timer:
            InstPVs(MagicMock(), MagicMock()).schedule()

        timer.assert_called_once()
        timer.return_value.start.assert_called_once()

    def test_update_pvs_from_mysql(self):
        mock_sql = MagicMock()
        mock_sql.query.return_value = [("pv1", "VAL"), ("pv2", "VAL RBV"), ("pv3", "5.0 VAL")]

        mock_producer = MagicMock()

        inst_pvs = InstPVs(mock_producer, mock_sql)
        inst_pvs.update_pvs_from_mysql()

        mock_producer.remove_config.assert_called_once_with([])
        self.assertCountEqual(
            mock_producer.add_config.call_args.args[0], ["pv1.VAL", "pv2.VAL", "pv2.RBV", "pv3.VAL"]
        )

        # Check that more calls where SQL query returns the same thing
        # don't cause extra updates
        inst_pvs.update_pvs_from_mysql()
        self.assertEqual(mock_producer.remove_config.call_count, 1)
        self.assertEqual(mock_producer.add_config.call_count, 1)

        # If SQL call does return something different then should update
        mock_sql.query.return_value = [("new_pv1", "VAL"), ("pv2", "VAL")]
        inst_pvs.update_pvs_from_mysql()

        self.assertCountEqual(
            mock_producer.remove_config.call_args.args[0], ["pv1.VAL", "pv2.RBV", "pv3.VAL"]
        )
        self.assertCountEqual(mock_producer.add_config.call_args.args[0], ["new_pv1.VAL"])
