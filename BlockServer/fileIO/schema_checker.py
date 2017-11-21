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

from __future__ import absolute_import
import os

from lxml import etree


class NotConfigFileException(Exception):
    def __init__(self, message):
        super(Exception,self).__init__(message)
        self.message = message


class ConfigurationIncompleteException(Exception):
    def __init__(self, message):
        super(Exception,self).__init__(message)
        self.message = message


class ConfigurationInvalidUnderSchema(Exception):
    def __init__(self, message):
        super(Exception,self).__init__(message)
        self.message = message


class ConfigurationFileBlank(Exception):
    def __init__(self, message):
        super(Exception,self).__init__(message)
        self.message = message


class ConfigurationSchemaChecker(object):
    """
    The ConfigurationSchemaChecker class.

    Contains utilities to check configurations against xml schema.
    """
    @staticmethod
    def check_xml_data_matches_schema(schema_filepath, xml_data):
        """
        This method takes xml data and checks it against a given schema.

        A ConfigurationInvalidUnderSchema error is raised if the file is incorrect.

        Args:
            schema_filepath (string): The location of the schema file
            xml_data (string): The XML data of the configuration
        """
        if len(xml_data) == 0:
            raise ConfigurationFileBlank("Invalid XML: File is blank.")

        folder, file_name = str.rsplit(schema_filepath, os.sep, 1)
        schema = ConfigurationSchemaChecker._get_schema(folder, file_name)

        try:
            # parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
            doc = etree.fromstring(ConfigurationSchemaChecker.encode_xml_string_as_bytes(xml_data))
            schema.assertValid(doc)
        except etree.DocumentInvalid as err:
            raise ConfigurationInvalidUnderSchema("{}".format(err))

    @staticmethod
    def encode_xml_string_as_bytes(xml_data):
        """
        Prepare an XML string to the format expected by ElementTree.

        Args:
            xml_data (str): input XML.

        Returns:
            Correctly encoded byte string.
        """
        return bytes(bytearray(xml_data, encoding='utf-8'))

    @staticmethod
    def check_xml_matches_schema(schema_filepath, screen_xml_data, object_type):
        try:
            ConfigurationSchemaChecker.check_xml_data_matches_schema(schema_filepath, screen_xml_data)
        except ConfigurationInvalidUnderSchema as err:
            raise ConfigurationInvalidUnderSchema(
                "{} incorrectly formatted: {}".format(object_type, err))

    @staticmethod
    def _check_file_against_schema(xml_file, schema_folder, schema_file):
        """
        This method takes an xml file and checks it against a given schema.

        Args:
            xml_file (string): The XML file to check
            schema_folder (string): The location of the schema files
            schema_file (string): The schema file to use

        Raises:
            etree.DocumentInvalid : Raised if the file is incorrect
        """
        schema = ConfigurationSchemaChecker._get_schema(schema_folder, schema_file)

        # Import the xml file
        with open(xml_file, 'r') as f:
            xml = f.read()

        doc = etree.fromstring(ConfigurationSchemaChecker.encode_xml_string_as_bytes(xml))
        schema.assertValid(doc)

    @staticmethod
    def _get_schema(schema_folder, schema_file):
        """
        This method generates an xml schemaq object for later use in validation.

        Args:
            schema_folder (string): The directory for schema files
            schema_file (string): The initial schema file
        """
        # must move to directory to handle schema includes
        cur = os.getcwd()
        os.chdir(schema_folder)
        with open(schema_file, 'r') as f:
            schema_raw = etree.XML(f.read().encode())

        schema = etree.XMLSchema(schema_raw)
        os.chdir(cur)

        return schema
