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
import os
import shutil
import traceback
import unittest
from importlib.resources import files

from server_common.file_path_manager import FILEPATH_MANAGER
from server_common.helpers import MACROS

from BlockServer.config.configuration import Configuration
from BlockServer.config.xml_converter import ConfigurationXmlConverter
from BlockServer.core.inactive_config_holder import InactiveConfigHolder
from BlockServer.fileIO.schema_checker import (
    ConfigurationInvalidUnderSchema,
    ConfigurationSchemaChecker,
)
from BlockServer.mocks.mock_file_manager import MockConfigurationFileManager

TEST_DIRECTORY = os.path.abspath("test_configs")
SCRIPT_DIRECTORY = os.path.abspath("test_scripts")

TEST_CONFIG = {
    "iocs": [
        {
            "simlevel": "devsim",
            "autostart": True,
            "restart": False,
            "macros": [{"name": "COMPORT", "value": "COM[0-9]+"}],
            "pvsets": [{"name": "SET", "enabled": "true"}],
            "pvs": [{"name": "NDWXXX:xxxx:SIMPLE:VALUE1", "value": "100"}],
            "name": "SIMPLE1",
            "component": None,
        },
        {
            "simlevel": "recsim",
            "autostart": False,
            "restart": True,
            "macros": [],
            "pvsets": [],
            "pvs": [],
            "name": "SIMPLE2",
            "component": None,
        },
    ],
    "blocks": [
        {
            "name": "testblock1",
            "local": True,
            "pv": "NDWXXX:xxxx:SIMPLE:VALUE1",
            "component": None,
            "visible": True,
        },
        {
            "name": "testblock2",
            "local": True,
            "pv": "NDWXXX:xxxx:SIMPLE:VALUE1",
            "component": None,
            "visible": True,
        },
        {
            "name": "testblock3",
            "local": True,
            "pv": "NDWXXX:xxxx:EUROTHERM1:RBV",
            "component": None,
            "visible": True,
            "runcontrol": False,
            "log_periodic": False,
            "log_rate": 5,
            "log_deadband": 0,
        },
    ],
    "components": [],
    "groups": [
        {"blocks": ["testblock1"], "name": "Group1", "component": None},
        {"blocks": ["testblock2"], "name": "Group2", "component": None},
        {"blocks": ["testblock3"], "name": "NONE", "component": None},
    ],
    "name": "TESTCONFIG1",
    "description": "A test configuration",
    "synoptic": "TEST_SYNOPTIC",
    "history": ["2015-02-16"],
}


def strip_out_whitespace(string):
    return string.strip().replace("    ", "").replace("\t", "")


class TestSchemaChecker(unittest.TestCase):
    def setUp(self):
        # Find the schema directory
        self.schema_dir = files("server_common.schema").joinpath("")

        FILEPATH_MANAGER.initialise(TEST_DIRECTORY, SCRIPT_DIRECTORY, self.schema_dir)
        self.cs = InactiveConfigHolder(MACROS, MockConfigurationFileManager())

    def tearDown(self):
        if os.path.isdir(TEST_DIRECTORY + os.sep):
            shutil.rmtree(os.path.abspath(TEST_DIRECTORY + os.sep))

    def test_valid_blocks_xml_matches_schema(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.blocks_to_xml(self.cs.get_block_details(), MACROS)

        try:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(
                os.path.join(self.schema_dir, "blocks.xsd"), xml
            )
        except:  # noqa: E722
            self.fail()

    def test_blocks_xml_does_not_match_schema_raises(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.blocks_to_xml(self.cs.get_block_details(), MACROS)

        # Keep it valid XML but don't match schema
        xml = xml.replace("visible>", "invisible>")

        self.assertRaises(
            ConfigurationInvalidUnderSchema,
            ConfigurationSchemaChecker.check_xml_data_matches_schema,
            os.path.join(self.schema_dir, "blocks.xsd"),
            xml,
        )

    def test_valid_groups_xml_matches_schema(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.groups_to_xml(self.cs.get_group_details())

        try:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(
                os.path.join(self.schema_dir, "groups.xsd"), xml
            )
        except Exception:
            self.fail(
                msg=f"Exception thrown from schema checker. Xml is {xml} exception is {traceback.format_exc()}"
            )

    def test_groups_xml_does_not_match_schema_raises(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.groups_to_xml(self.cs.get_group_details())

        # Keep it valid XML but don't match schema
        xml = xml.replace("<block ", "<notblock ")

        self.assertRaises(
            ConfigurationInvalidUnderSchema,
            ConfigurationSchemaChecker.check_xml_data_matches_schema,
            os.path.join(self.schema_dir, "groups.xsd"),
            xml,
        )

    def test_valid_iocs_xml_matches_schema(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.iocs_to_xml(self.cs.get_ioc_details())

        try:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(
                os.path.join(self.schema_dir, "iocs.xsd"), xml
            )
        except Exception:
            self.fail(
                msg=f"Exception thrown from schema checker. Xml is {xml} exception is {traceback.format_exc()}"
            )

    def test_iocs_xml_does_not_match_schema_raises(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.iocs_to_xml(self.cs.get_ioc_details())

        # Keep it valid XML but don't match schema
        xml = xml.replace("<macro ", "<nacho ")

        self.assertRaises(
            ConfigurationInvalidUnderSchema,
            ConfigurationSchemaChecker.check_xml_data_matches_schema,
            os.path.join(self.schema_dir, "iocs.xsd"),
            xml,
        )

    def test_valid_meta_xml_matches_schema(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.meta_to_xml(self.cs.get_config_meta())

        try:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(
                os.path.join(self.schema_dir, "meta.xsd"), xml
            )
        except:  # noqa: E722
            self.fail()

    def test_meta_xml_does_not_match_schema_raises(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.meta_to_xml(self.cs.get_config_meta())

        # Keep it valid XML but don't match schema
        xml = xml.replace("synoptic>", "snyoptic>")

        self.assertRaises(
            ConfigurationInvalidUnderSchema,
            ConfigurationSchemaChecker.check_xml_data_matches_schema,
            os.path.join(self.schema_dir, "meta.xsd"),
            xml,
        )

    def test_valid_components_xml_matches_schema(self):
        conf = Configuration(MACROS)
        conf.components["COMP1"] = "COMP1"
        conf.components["COMP2"] = "COMP2"

        xml = ConfigurationXmlConverter.components_to_xml(conf.components)

        try:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(
                os.path.join(self.schema_dir, "components.xsd"), xml
            )
        except:  # noqa: E722
            self.fail()

    def test_components_xml_does_not_match_schema_raises(self):
        conf = Configuration(MACROS)
        conf.components["COMP1"] = "COMP1"
        conf.components["COMP2"] = "COMP2"

        xml = ConfigurationXmlConverter.components_to_xml(conf.components)

        # Keep it valid XML but don't match schema
        xml = xml.replace("<component ", "<domponent ")

        self.assertRaises(
            ConfigurationInvalidUnderSchema,
            ConfigurationSchemaChecker.check_xml_data_matches_schema,
            os.path.join(self.schema_dir, "meta.xsd"),
            xml,
        )

    def test_cannot_find_schema_raises(self):
        self.cs.set_config_details(TEST_CONFIG)
        xml = ConfigurationXmlConverter.blocks_to_xml(self.cs.get_block_details(), MACROS)

        self.assertRaises(
            IOError,
            ConfigurationSchemaChecker.check_xml_data_matches_schema,
            os.path.join(self.schema_dir, "does_not_exist.xsd"),
            xml,
        )
