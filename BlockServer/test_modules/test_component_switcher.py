import os
import sys
import types
import unittest
from queue import Queue
from typing import Any, Dict, List, Tuple
from unittest import mock
from unittest.mock import MagicMock

from BlockServer.component_switcher.component_switcher import ComponentSwitcher
from BlockServer.core.macros import PVPREFIX_MACRO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class MockChannelAccess(object):
    MONITORS: List[Tuple[str, types.FunctionType]] = []

    @staticmethod
    def add_monitor(pv: str, callback_func: types.FunctionType):
        MockChannelAccess.MONITORS.append((pv, callback_func))


class MockConfigListManager(object):
    def __init__(self):
        self.active_config_name = "active"
        self.configs = ["active", "inactive1", "inactive2"]
        self.components = ["comp1", "comp2"]
        self.loaded_configs = {}  # config/comp name : returned config

    def get_configs(self):
        return [{"name": conf_name} for conf_name in self.configs]

    def get_components(self):
        return [{"name": comp_name} for comp_name in self.components]

    def load_config(self, name, *_, **__):
        if name in self.loaded_configs:
            return self.loaded_configs[name]
        else:
            return MagicMock()

    def update(self, *args, **kwargs):
        pass


class MockComponentSwitcherFileManager(object):
    def __init__(self):
        self.config = None

    def read_config(self) -> List[Dict[str, Any]]:
        return self.config


class TestComponentSwitcher(unittest.TestCase):
    def setUp(self) -> None:
        MockChannelAccess.MONITORS = []

        self.config_list = MockConfigListManager()
        self.write_queue = Queue()
        self.reload_func = MagicMock()
        self.file_manager = MockComponentSwitcherFileManager()

        self.file_manager.config = [
            {
                "pv": "first",
                "is_local": True,
                "value_to_component_map": {
                    "A": "comp1",
                    "B": "comp2",
                },
            }
        ]

        self.component_switcher = ComponentSwitcher(
            config_list=self.config_list,
            blockserver_write_queue=self.write_queue,
            reload_current_config_func=self.reload_func,
            file_manager=self.file_manager,
            channel_access_class=MockChannelAccess,
        )

    def test_GIVEN_empty_config_file_WHEN_call_add_monitors_THEN_no_monitors_added(self):
        self.file_manager.config = []

        self.component_switcher.create_monitors()

        self.assertEqual(len(MockChannelAccess.MONITORS), 0)

    def test_GIVEN_2_pvs_in_config_file_WHEN_call_add_monitors_THEN_2_monitors_added(self):
        self.file_manager.config = [
            {"pv": "first", "is_local": False, "value_to_component_map": {}},
            {"pv": "second", "is_local": False, "value_to_component_map": {}},
        ]

        self.component_switcher.create_monitors()

        self.assertEqual(len(MockChannelAccess.MONITORS), 2)
        self.assertEqual(MockChannelAccess.MONITORS[0][0], "first")
        self.assertEqual(MockChannelAccess.MONITORS[1][0], "second")

    @mock.patch.dict("BlockServer.core.macros.MACROS", {PVPREFIX_MACRO: "some_prefix:"})
    def test_GIVEN_local_pv_monitored_THEN_monitored_pv_has_local_prefix_appended(self):
        self.file_manager.config = [{"pv": "first", "is_local": True, "value_to_component_map": {}}]

        self.component_switcher.create_monitors()
        self.assertEqual(MockChannelAccess.MONITORS[0][0], "some_prefix:first")

    @mock.patch.dict("BlockServer.core.macros.MACROS", {PVPREFIX_MACRO: "some_prefix:"})
    def test_GIVEN_non_local_pv_monitored_THEN_monitored_pv_does_not_have_local_prefix_appended(
        self,
    ):
        self.file_manager.config = [
            {"pv": "first", "is_local": False, "value_to_component_map": {}}
        ]

        self.component_switcher.create_monitors()
        self.assertEqual(MockChannelAccess.MONITORS[0][0], "first")

    def test_GIVEN_monitor_is_triggered_THEN_action_gets_appended_to_bs_write_queue(self):
        self.component_switcher.create_monitors()

        self.assertEqual(len(MockChannelAccess.MONITORS), 1)

        self.assertEqual(self.write_queue.qsize(), 0)
        # Fire the monitor with value A
        MockChannelAccess.MONITORS[0][1]("A", 0, 0)

        self.assertEqual(self.write_queue.qsize(), 1)
        func, args, status = self.write_queue.get()

        self.assertEqual(func, self.component_switcher._edit_all_configurations)
        # Component 2 should be removed, components 1 should be added as our monitor got value A
        self.assertEqual(args, ({"comp2"}, {"comp1"}))

    def test_GIVEN_monitor_is_triggered_with_non_zero_stat_THEN_action_is_ignored(self):
        self.component_switcher.create_monitors()

        self.assertEqual(len(MockChannelAccess.MONITORS), 1)

        self.assertEqual(self.write_queue.qsize(), 0)
        # Fire the monitor with value A and stat=1
        MockChannelAccess.MONITORS[0][1]("A", 1, 0)

        self.assertEqual(self.write_queue.qsize(), 0)

    def test_GIVEN_monitor_is_triggered_with_non_zero_sevr_THEN_action_is_ignored(self):
        self.component_switcher.create_monitors()

        self.assertEqual(len(MockChannelAccess.MONITORS), 1)

        self.assertEqual(self.write_queue.qsize(), 0)
        # Fire the monitor with value A and sevr=1
        MockChannelAccess.MONITORS[0][1]("A", 0, 1)

        self.assertEqual(self.write_queue.qsize(), 0)

    def test_GIVEN_monitor_is_triggered_with_an_unknown_value_THEN_action_does_not_get_appended_to_bs_write_queue(
        self,
    ):
        self.component_switcher.create_monitors()

        self.assertEqual(len(MockChannelAccess.MONITORS), 1)

        self.assertEqual(self.write_queue.qsize(), 0)
        # Fire the monitor with a fake (invalid) value
        MockChannelAccess.MONITORS[0][1]("C", 0, 0)
        self.assertEqual(self.write_queue.qsize(), 0)

    def test_GIVEN_active_config_is_not_in_config_list_THEN_get_valueerror(self):
        self.config_list.active_config_name = "invalid"
        with self.assertRaises(ValueError):
            self.component_switcher._edit_all_configurations(set(), set())

    def test_GIVEN_component_to_be_removed_doesnt_exist_THEN_get_valueerror(self):
        with self.assertRaises(ValueError):
            self.component_switcher._edit_all_configurations({"nonexistent"}, set())

    def test_GIVEN_component_to_be_added_doesnt_exist_THEN_get_valueerror(self):
        with self.assertRaises(ValueError):
            self.component_switcher._edit_all_configurations(set(), {"nonexistent"})

    def test_GIVEN_no_components_to_be_added_or_removed_THEN_current_config_not_reloaded(self):
        self.component_switcher._edit_all_configurations(set(), set())

        self.assertFalse(self.reload_func.called)

    def test_GIVEN_components_to_added_or_removed_THEN_current_config_reloaded(self):
        self.component_switcher._edit_all_configurations({"comp1"}, {"comp2"})

        self.assertTrue(self.reload_func.called)

    def test_GIVEN_active_config_already_in_correct_state_THEN_not_saved_again(self):
        mock_conf = MagicMock()
        mock_conf.get_component_names.return_value = ["comp1"]

        self.config_list.loaded_configs = {"active": mock_conf}

        self.component_switcher._edit_all_configurations(
            components_to_be_added={"comp1"}, components_to_be_removed={"comp2"}
        )

        self.assertFalse(mock_conf.save_inactive.called)
        self.assertFalse(self.reload_func.called)

    def test_GIVEN_active_config_not_in_correct_state_THEN_edited_and_saved(self):
        mock_conf = MagicMock()
        mock_conf.get_component_names.return_value = ["comp1"]

        self.config_list.loaded_configs = {"active": mock_conf}

        self.component_switcher._edit_all_configurations(
            components_to_be_added={"comp2"}, components_to_be_removed={"comp1"}
        )

        mock_conf.remove_comp.assert_called_with("comp1")
        mock_conf.add_component.assert_called_with("comp2")
        self.assertTrue(mock_conf.save_inactive.called)
        self.assertTrue(self.reload_func.called)
