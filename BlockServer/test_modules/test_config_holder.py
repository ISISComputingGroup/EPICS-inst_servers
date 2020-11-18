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

import unittest
import os
import stat

from BlockServer.core.config_holder import ConfigHolder
from BlockServer.config.configuration import Configuration
from BlockServer.core.constants import DEFAULT_COMPONENT
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.core.macros import MACROS
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager


CONFIG_PATH = "./test_configs/"
BASE_PATH = "./example_base/"


# Helper functions
def add_block(ch, name, pv, group, local=True):
    data = {'name': name, 'pv': pv, 'group': group, 'local': local}
    ch.add_block(data)


def create_dummy_config():
    config = Configuration(MACROS)
    config.add_block("TESTBLOCK1", "PV1", "GROUP1", True)
    config.add_block("TESTBLOCK2", "PV2", "GROUP2", True)
    config.add_block("TESTBLOCK3", "PV3", "GROUP2", True)
    config.add_block("TESTBLOCK4", "PV4", "NONE", False)
    config.add_ioc("SIMPLE1")
    config.add_ioc("SIMPLE2")
    config.set_name("DUMMY")
    return config


def create_dummy_component():
    config = Configuration(MACROS)
    config.add_block("COMPBLOCK1", "PV1", "GROUP1", True)
    config.add_block("COMPBLOCK2", "PV2", "COMPGROUP", True)
    config.add_ioc("COMPSIMPLE1")
    return config


def on_rm_error(func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)


def create_default_test_config_holder():
    ch = InactiveConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                      test_config=create_dummy_config())
    return ch


class TestConfigHolderSequence(unittest.TestCase):
    def setUp(self):
        # Note: all configs are saved in memory
        pass

    def tearDown(self):
        pass

    def test_dummy_name(self):
        ch = create_default_test_config_holder()
        self.assertEqual(ch.get_config_name(), "DUMMY")

    def test_getting_blocks_json_with_no_blocks_returns_empty_list(self):
        # arrange
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(), test_config=None)
        # act
        blocks = ch.get_blocknames()
        # assert
        self.assertEqual(len(blocks), 0)

    def test_dummy_config_blocks(self):
        ch = create_default_test_config_holder()

        blks = ch.get_blocknames()
        self.assertEqual(len(blks), 4)
        self.assertEqual(blks[0], "TESTBLOCK1")
        self.assertEqual(blks[1], "TESTBLOCK2")
        self.assertEqual(blks[2], "TESTBLOCK3")
        self.assertEqual(blks[3], "TESTBLOCK4")

        blk_details = ch.get_block_details()
        self.assertEqual(len(blk_details), 4)
        self.assertTrue("TESTBLOCK1".lower() in blk_details)
        self.assertTrue("TESTBLOCK2".lower() in blk_details)
        self.assertTrue("TESTBLOCK3".lower() in blk_details)
        self.assertTrue("TESTBLOCK4".lower() in blk_details)
        self.assertEqual(blk_details["TESTBLOCK1".lower()].pv, "PV1")
        self.assertEqual(blk_details["TESTBLOCK2".lower()].pv, "PV2")
        self.assertEqual(blk_details["TESTBLOCK3".lower()].pv, "PV3")
        self.assertEqual(blk_details["TESTBLOCK4".lower()].pv, "PV4")
        self.assertEqual(blk_details["TESTBLOCK1".lower()].local, True)
        self.assertEqual(blk_details["TESTBLOCK2".lower()].local, True)
        self.assertEqual(blk_details["TESTBLOCK3".lower()].local, True)
        self.assertEqual(blk_details["TESTBLOCK4".lower()].local, False)


    def test_dummy_config_blocks_add_component(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)

        blks = ch.get_blocknames()
        self.assertEqual(len(blks), 6)
        self.assertEqual(blks[4], "COMPBLOCK1")
        self.assertEqual(blks[5], "COMPBLOCK2")

        blk_details = ch.get_block_details()
        self.assertEqual(len(blk_details), 6)
        self.assertTrue("COMPBLOCK1".lower() in blk_details)
        self.assertTrue("COMPBLOCK2".lower() in blk_details)
        self.assertEqual(blk_details["COMPBLOCK1".lower()].pv, "PV1")
        self.assertEqual(blk_details["COMPBLOCK2".lower()].pv, "PV2")
        self.assertEqual(blk_details["TESTBLOCK1".lower()].local, True)

    def test_dummy_config_blocks_add_remove_component(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)

        ch.remove_comp("TESTCOMPONENT")

        blks = ch.get_blocknames()
        self.assertEqual(len(blks), 4)
        self.assertFalse("COMPBLOCK1" in blks)
        self.assertFalse("COMPBLOCK2" in blks)

    def test_dummy_config_groups(self):
        ch = create_default_test_config_holder()

        grp_details = ch.get_group_details()
        self.assertEqual(len(grp_details), 3)
        self.assertTrue("GROUP1".lower() in grp_details)
        self.assertTrue("GROUP2".lower() in grp_details)
        self.assertTrue("NONE".lower() in grp_details)
        self.assertTrue("TESTBLOCK1" in grp_details["GROUP1".lower()].blocks)
        self.assertTrue("TESTBLOCK2" in grp_details["GROUP2".lower()].blocks)
        self.assertTrue("TESTBLOCK3" in grp_details["GROUP2".lower()].blocks)
        self.assertTrue("TESTBLOCK4" in grp_details["NONE".lower()].blocks)

    def test_dummy_config_groups_add_component(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)

        grp_details = ch.get_group_details()
        self.assertEqual(len(grp_details), 4)
        self.assertTrue("COMPGROUP".lower() in grp_details)
        self.assertTrue("COMPBLOCK1" in grp_details["GROUP1".lower()].blocks)
        self.assertTrue("COMPBLOCK2" in grp_details["COMPGROUP".lower()].blocks)

    def test_dummy_config_groups_add_remove_component(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)
        ch.remove_comp("TESTCOMPONENT")

        grp_details = ch.get_group_details()
        self.assertEqual(len(grp_details), 3)
        self.assertFalse("COMPGROUP".lower() in grp_details)
        self.assertFalse("COMPBLOCK1" in grp_details["GROUP1".lower()].blocks)

    def test_dummy_config_iocs(self):
        ch = create_default_test_config_holder()

        ioc_names = ch.get_ioc_names()
        self.assertEqual(len(ioc_names), 2)
        self.assertTrue("SIMPLE1" in ioc_names)
        self.assertTrue("SIMPLE2" in ioc_names)

    def test_dummy_config_iocs_add_component(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)

        ioc_names = ch.get_ioc_names()
        self.assertEqual(len(ioc_names), 3)
        self.assertTrue("COMPSIMPLE1" in ioc_names)

    def test_dummy_config_iocs_add_remove_component(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)
        ch.remove_comp("TESTCOMPONENT")

        ioc_names = ch.get_ioc_names()
        self.assertEqual(len(ioc_names), 2)
        self.assertFalse("COMPSIMPLE1" in ioc_names)

    def test_dummy_config_components(self):
        ch = create_default_test_config_holder()

        comps = ch.get_component_names()
        self.assertEqual(len(comps), 0)

    def test_dummy_config_components_add_component(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)

        comps = ch.get_component_names()
        self.assertEqual(len(comps), 1)
        self.assertTrue("TESTCOMPONENT" in comps)

    def test_dummy_config_components_add_remove_component(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)
        ch.remove_comp("TESTCOMPONENT")

        comps = ch.get_component_names()
        self.assertEqual(len(comps), 0)
        self.assertFalse("TESTCOMPONENT".lower() in comps)

    def test_add_block(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))

        blk = {"name": "TESTBLOCK1", "pv": "PV1", "local": True, "group": "NONE"}
        ch.add_block(blk)

        blk_details = ch.get_block_details()
        self.assertEqual(len(blk_details), 1)
        self.assertTrue("TESTBLOCK1".lower() in blk_details)
        self.assertEqual(blk_details["TESTBLOCK1".lower()].pv, "PV1")
        self.assertEqual(blk_details["TESTBLOCK1".lower()].local, True)

    def test_add_ioc(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))

        ch._add_ioc("TESTIOC1")

        ioc_details = ch.get_ioc_names()
        self.assertEqual(len(ioc_details), 1)
        self.assertTrue("TESTIOC1" in ioc_details)

    def test_add_ioc_component(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))

        ch.add_component("TESTCOMPONENT", Configuration(MACROS))
        ch._add_ioc("TESTIOC1", "TESTCOMPONENT")

        ioc_details = ch.get_ioc_names()
        self.assertEqual(len(ioc_details), 1)
        self.assertTrue("TESTIOC1" in ioc_details)

    def test_get_config_details_empty(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))
        details = ch.get_config_details()

        self.assertEqual(len(details['blocks']), 0)
        self.assertEqual(len(details['groups']), 0)
        self.assertEqual(len(details['iocs']), 0)
        self.assertEqual(len(details['components']), 0)
        self.assertEqual(details['name'], "")
        self.assertEqual(details['description'], "")
        self.assertEqual(details['synoptic'], "")

    def test_get_config_details(self):
        ch = create_default_test_config_holder()
        details = ch.get_config_details()

        self.assertEqual(details["name"], "DUMMY")
        self.assertEqual(len(details['blocks']), 4)
        blks = [x['name'] for x in details['blocks']]
        self.assertTrue("TESTBLOCK1" in blks)
        self.assertTrue("TESTBLOCK2" in blks)
        self.assertTrue("TESTBLOCK3" in blks)
        self.assertTrue("TESTBLOCK4" in blks)
        self.assertEqual(len(details['groups']), 3)
        self.assertEqual(details['groups'][0]['blocks'], ["TESTBLOCK1"])
        self.assertEqual(details['groups'][1]['blocks'], ["TESTBLOCK2", "TESTBLOCK3"])
        self.assertEqual(details['groups'][2]['blocks'], ["TESTBLOCK4"])
        self.assertEqual(len(details['iocs']), 2)
        iocs = [x['name'] for x in details['iocs']]
        self.assertTrue("SIMPLE1" in iocs)
        self.assertTrue("SIMPLE2" in iocs)
        self.assertEqual(len(details['components']), 0)

    def test_get_config_details_add_component(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)

        details = ch.get_config_details()
        self.assertEqual(len(details['blocks']), 2)
        blks = [x['name'] for x in details['blocks']]
        self.assertTrue("COMPBLOCK1" in blks)
        self.assertTrue("COMPBLOCK2" in blks)
        self.assertEqual(len(details['groups']), 2)
        self.assertEqual(details['groups'][0]['blocks'], ["COMPBLOCK1"])
        self.assertEqual(details['groups'][1]['blocks'], ["COMPBLOCK2"])
        self.assertEqual(len(details['iocs']), 0)
        iocs = [x['name'] for x in details['iocs']]
        self.assertFalse("COMPSIMPLE1" in iocs)
        self.assertEqual(len(details['components']), 1)

    def test_empty_config_save_and_load(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))
        ch.save_configuration("TESTCONFIG", False)
        ch.clear_config()

        conf = ch.load_configuration("TESTCONFIG")
        ch.set_config(conf, False)

        self.assertEqual(ch.get_config_name(), "TESTCONFIG")
        self.assertEqual(len(ch.get_blocknames()), 0)
        self.assertEqual(len(ch.get_group_details()), 0)
        self.assertEqual(len(ch.get_ioc_names()), 0)
        self.assertEqual(len(ch.get_component_names()), 0)

    def test_empty_component_save_and_load(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))
        ch.save_configuration("TESTCOMPONENT", True)
        ch.clear_config()

        conf = ch.load_configuration("TESTCOMPONENT", True)
        ch.set_config(conf, True)

        self.assertEqual(ch.get_config_name(), "TESTCOMPONENT")
        self.assertEqual(len(ch.get_blocknames()), 0)
        self.assertEqual(len(ch.get_group_details()), 0)
        self.assertEqual(len(ch.get_ioc_names()), 0)
        self.assertEqual(len(ch.get_component_names()), 0)

    def test_dummy_config_save_and_load(self):
        ch = create_default_test_config_holder()
        ch.save_configuration("TESTCONFIG", False)
        ch.clear_config()

        conf = ch.load_configuration("TESTCONFIG")
        ch.set_config(conf, False)

        self.assertEqual(ch.get_config_name(), "TESTCONFIG")
        self.assertEqual(len(ch.get_blocknames()), 4)
        self.assertEqual(len(ch.get_group_details()), 3)
        self.assertEqual(len(ch.get_ioc_names()), 2)
        self.assertEqual(len(ch.get_component_names()), 0)

    def test_save_comp_add_to_config(self):
        # Create and save a component
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=create_dummy_component())
        ch.save_configuration("TESTCOMPONENT", True)
        ch.clear_config()

        # Create and save a config that uses the component
        ch.set_config(create_dummy_config())
        comp = ch.load_configuration("TESTCOMPONENT", True)
        ch.add_component("TESTCOMPONENT", comp)

        ch.save_configuration("TESTCONFIG", False)
        ch.clear_config()
        conf = ch.load_configuration("TESTCONFIG", False)
        ch.set_config(conf)

        self.assertEqual(len(ch.get_component_names()), 1)

    def test_get_groups_list_from_empty_repo(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager())
        grps = ch.get_group_details()
        self.assertEqual(len(grps), 0)

    def test_add_config_and_get_groups_list(self):
        ch = create_default_test_config_holder()

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 3)
        self.assertTrue('group1' in grps)
        self.assertTrue('group2' in grps)
        self.assertTrue("TESTBLOCK1" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK2" in grps['group2'].blocks)
        self.assertTrue("TESTBLOCK3" in grps['group2'].blocks)
        self.assertTrue("TESTBLOCK4" in grps['none'].blocks)

    def test_add_component_then_get_groups_list(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 4)
        self.assertTrue('compgroup' in grps)
        self.assertTrue("COMPBLOCK1" in grps['group1'].blocks)
        self.assertTrue("COMPBLOCK2" in grps['compgroup'].blocks)

    def test_add_component_remove_component_then_get_groups_list(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)
        ch.remove_comp("TESTCOMPONENT")

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 3)
        self.assertFalse('compgroup' in grps)
        self.assertFalse("COMPBLOCK1" in grps['group1'].blocks)

    def test_redefine_groups_from_list_simple_move(self):
        ch = create_default_test_config_holder()

        # Move TESTBLOCK2 and TESTBLOCK4 into group 1
        redef = [{"name": "group1", "blocks": ["TESTBLOCK1", "TESTBLOCK2", "TESTBLOCK4"], "component": None},
                 {"name": "group2", "blocks": ["TESTBLOCK3"], "component": None}]
        ch._set_group_details(redef)

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 2)
        self.assertTrue('group1' in grps)
        self.assertTrue('group2' in grps)
        self.assertTrue("TESTBLOCK1" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK2" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK3" in grps['group2'].blocks)
        self.assertTrue("TESTBLOCK4" in grps['group1'].blocks)

    def test_redefine_groups_from_list_leave_group_empty(self):
        ch = create_default_test_config_holder()

        # Move TESTBLOCK2, TESTBLOCK3 and TESTBLOCK4 into group 1
        redef = [{"name": "group1", "blocks": ["TESTBLOCK1", "TESTBLOCK2", "TESTBLOCK3", "TESTBLOCK4"]
                     , "component": None},
                 {"name": "group2", "blocks": [], "component": None}]
        ch._set_group_details(redef)

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 1)  # The group1
        self.assertTrue('group1' in grps)
        self.assertFalse('group2' in grps)
        self.assertTrue("TESTBLOCK1" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK2" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK3" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK4" in grps['group1'].blocks)

    def test_redefine_groups_from_list_component_changes(self):
        ch = create_default_test_config_holder()
        comp = create_dummy_component()
        ch.add_component("TESTCOMPONENT", comp)

        # Move COMPBLOCK1 and COMPBLOCK2 into group 1
        redef = [{"name": "group1", "blocks": ["TESTBLOCK1", "TESTBLOCK2", "TESTBLOCK3", "TESTBLOCK4", "COMPBLOCK1",
                                               "COMPBLOCK2"], "component": None},
                 {"name": "group2", "blocks": [], "component": None},
                 {"name": "compgroup", "blocks": [], "component": None}]
        ch._set_group_details(redef)

        grps = ch.get_group_details()
        self.assertEqual(len(grps), 1)  # group1
        self.assertTrue('group1' in grps)
        self.assertFalse('group2' in grps)
        self.assertFalse('compgroup' in grps)
        self.assertTrue("TESTBLOCK1" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK2" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK3" in grps['group1'].blocks)
        self.assertTrue("TESTBLOCK4" in grps['group1'].blocks)

    def test_set_config_details(self):
        # Need component
        ch = InactiveConfigHolder(MACROS, file_manager=MockConfigurationFileManager(), test_config=Configuration(MACROS))
        ch.save_configuration("TESTCOMPONENT", True)

        new_details = {"iocs":
                           [{"name": "TESTSIMPLE1", "autostart": True, "restart": True, "macros": [], "pvs": [],
                             "pvsets": [], "component": None},
                            {"name": "TESTSIMPLE2", "autostart": True, "restart": True, "macros": [], "pvs": [],
                             "pvsets": [], "component": None}],
                       "blocks":
                           [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "component": None,
                             "visible": True},
                            {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "component": None,
                             "visible": True},
                            {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "component": None,
                             "visible": True}],
                       "components": [{"name": "TESTCOMPONENT"}],
                       "groups":
                           [{"blocks": ["TESTBLOCK1"], "name": "Group1", "component": None},
                            {"blocks": ["TESTBLOCK2"], "name": "Group2", "component": None},
                            {"blocks": ["TESTBLOCK3"], "name": "NONE", "component": None}],
                       "name": "TESTCONFIG",
                       "description": "Test Description",
                       "synoptic": "TEST_SYNOPTIC"
                       }
        ch.set_config_details(new_details)
        details = ch.get_config_details()
        iocs = [x['name'] for x in details['iocs']]
        self.assertEqual(len(iocs), 2)
        self.assertTrue("TESTSIMPLE1" in iocs)
        self.assertTrue("TESTSIMPLE2" in iocs)

        self.assertEqual(len(details['blocks']), 3)
        blks = [x['name'] for x in details['blocks']]
        self.assertTrue("TESTBLOCK1" in blks)
        self.assertTrue("TESTBLOCK2" in blks)
        self.assertTrue("TESTBLOCK3" in blks)

        self.assertEqual(len(details['groups']), 3)
        self.assertEqual(details['groups'][0]['blocks'], ["TESTBLOCK1"])
        self.assertEqual(details['groups'][1]['blocks'], ["TESTBLOCK2"])
        self.assertEqual(details['groups'][2]['blocks'], ["TESTBLOCK3"])

        self.assertEqual(len(details['components']), 1)
        self.assertEqual(details['components'][0]['name'], "TESTCOMPONENT")

        self.assertEqual(details['name'], "TESTCONFIG")
        self.assertEqual(details['description'], "Test Description")
        self.assertEqual(details['synoptic'], "TEST_SYNOPTIC")

    def test_set_config_details_nonexistant_block_in_group_is_removed(self):
        ch = create_default_test_config_holder()

        new_details = {"iocs":
                           [{"name": "TESTSIMPLE1", "autostart": True, "restart": True, "macros": [], "pvs": [],
                             "pvsets": [], "component": None},
                            {"name": "TESTSIMPLE2", "autostart": True, "restart": True, "macros": [], "pvs": [],
                             "pvsets": [], "component": None}],
                       "blocks":
                           [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "component": None,
                             "visible": True},
                            {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "component": None,
                             "visible": True},
                            {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "component": None,
                             "visible": True}],
                       "components": [],
                       "groups":
                           [{"blocks": ["TESTBLOCK1", "IDONTEXIST"], "name": "Group1", "component": None},
                            {"blocks": ["TESTBLOCK2"], "name": "Group2", "component": None},
                            {"blocks": ["TESTBLOCK3"], "name": "NONE", "component": None}],
                       "name": "TESTCONFIG"
        }
        ch.set_config_details(new_details)

        # Check via get_config_details
        details = ch.get_config_details()
        self.assertEqual(len(details['blocks']), 3)
        blks = [x['name'] for x in details['blocks']]
        self.assertFalse("IDONTEXIST" in blks)

        self.assertEqual(len(details['groups']), 3)
        self.assertEqual(details['groups'][0]['blocks'], ["TESTBLOCK1"])

        # Also check via get_group_details
        grp = ch.get_group_details()['group1']
        self.assertFalse("IDONTEXIST" in grp.blocks)

    def test_set_config_details_empty_group_is_removed(self):
        ch = create_default_test_config_holder()

        new_details = {"iocs":
                           [{"name": "TESTSIMPLE1", "autostart": True, "restart": True, "macros": {}, "pvs": {},
                             "pvsets": {}, "component": None},
                            {"name": "TESTSIMPLE2", "autostart": True, "restart": True, "macros": {}, "pvs": {},
                             "pvsets": {}, "component": None}],
                       "blocks":
                           [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "component": None,
                             "visible": True},
                            {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "component": None,
                             "visible": True},
                            {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "component": None,
                             "visible": True}],
                       "components": [],
                       "groups":
                           [{"blocks": ["TESTBLOCK1", "TESTBLOCK2"], "name": "Group1", "component": None},
                            {"blocks": [], "name": "Group2", "component": None},
                            {"blocks": ["TESTBLOCK3"], "name": "NONE", "component": None}],
                       "name": "TESTCONFIG"
        }
        ch.set_config_details(new_details)

        # Check via get_config_details
        details = ch.get_config_details()
        self.assertEqual(len(details['groups']), 2)

        # Also check via get_group_details
        grps = ch.get_group_details()
        self.assertEqual(len(grps), 2)

    def test_set_config_details_ioc_lists_filled(self):
        ch = create_default_test_config_holder()
        new_details = {"iocs":
                           [{"name": "TESTSIMPLE1", "autostart": True, "restart": True,
                                "macros": [{"name": "TESTMACRO1", "value" : "TEST"}, {"name": "TESTMACRO2",
                                                                                      "value" : 123}],
                                "pvs": [{"name": "TESTPV1", "value": 123}],
                                "pvsets": [{"name": "TESTPVSET1", "enabled": True}],
                                "component": None},
                            {"name": "TESTSIMPLE2", "autostart": True, "restart": True,
                                "macros": [{"name": "TESTMACRO3", "value" : "TEST2"}],
                                "pvs": [],
                                "pvsets": [],
                                "component": None}],
                       "blocks":
                           [{"name": "TESTBLOCK1", "local": True, "pv": "PV1", "component": None,
                             "visible": True},
                            {"name": "TESTBLOCK2", "local": True, "pv": "PV2", "component": None,
                             "visible": True},
                            {"name": "TESTBLOCK3", "local": True, "pv": "PV3", "component": None,
                             "visible": True}],
                       "components": [],
                       "groups":
                           [{"blocks": ["TESTBLOCK1", "IDONTEXIST"], "name": "Group1", "component": None},
                            {"blocks": ["TESTBLOCK2"], "name": "Group2", "component": None},
                            {"blocks": ["TESTBLOCK3"], "name": "NONE", "component": None}],
                       "name": "TESTCONFIG"
        }
        ch.set_config_details(new_details)

        # Check via get_config_details
        details = ch.get_config_details()
        self.assertEqual(len(details['iocs']), 2)
        macros = [y for x in details['iocs'] for y in x['macros']]
        macro_names = [x['name'] for x in macros]
        self.assertTrue("TESTMACRO1" in macro_names)
        self.assertTrue("TESTMACRO3" in macro_names)

    def test_set_config_details_empty_config(self):
        ch = create_default_test_config_holder()
        new_details = {"iocs": [],
                       "blocks": [],
                       "components": [],
                       "groups": [],
                       "name": "EMPTYCONFIG",
                       "description": "",
                       "synoptic": ""
        }
        ch.set_config_details(new_details)

        # Check via get_config_details
        details = ch.get_config_details()
        self.assertEqual(len(details['iocs']), 0)
        self.assertEqual(len(details['blocks']), 0)
        self.assertEqual(len(details['components']), 0)
        self.assertEqual(len(details['groups']), 0)
        self.assertEqual(details['description'], "")
        self.assertEqual(details['synoptic'], "")
        self.assertEqual(details['name'], "EMPTYCONFIG")

    def test_default_component_is_loaded(self):
        # Arrange
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))
        ch.save_configuration("TESTCONFIG", False)
        ch.clear_config()

        # Act
        conf = ch.load_configuration("TESTCONFIG")
        ch.set_config(conf, False)

        # Assert
        comp_count = len(ch.get_component_names())
        comp_count_with_default = len(ch.get_component_names(True))
        self.assertTrue(comp_count_with_default > comp_count)

    def test_cannot_modify_default(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(), test_config=Configuration(MACROS))

        try:
            ch.save_configuration(DEFAULT_COMPONENT, True)
        except Exception as err:
            self.assertEqual(str(err), "Cannot save over default component")

    def test_clear_config(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(), test_config=None)
        add_block(ch, "TESTBLOCK1", "PV1", "GROUP1", True)
        add_block(ch, "TESTBLOCK2", "PV2", "GROUP2", True)
        add_block(ch, "TESTBLOCK3", "PV3", "GROUP2", True)
        add_block(ch, "TESTBLOCK4", "PV4", "NONE", True)
        blocks = ch.get_blocknames()
        self.assertEqual(len(blocks), 4)
        ch.clear_config()
        blocks = ch.get_blocknames()
        self.assertEqual(len(blocks), 0)

    def test_cannot_save_with_blank_name(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))
        self.assertRaises(Exception, ch.save_configuration, "", False)

    def test_cannot_save_with_none_name(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))
        self.assertRaises(Exception, ch.save_configuration, None, False)

    def test_cannot_save_with_invalid_name(self):
        ch = ConfigHolder(MACROS, file_manager=MockConfigurationFileManager(),
                          test_config=Configuration(MACROS))
        self.assertRaises(Exception, ch.save_configuration, "This is invalid", False)
        self.assertRaises(Exception, ch.save_configuration, "This_is_invalid!", False)
