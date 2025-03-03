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
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.getcwd()))

import argparse

from lxml import etree

from server_common.utilities import print_and_log


def validate(schema_file: os.PathLike[str], xml_file: os.PathLike[str]) -> None:
    print(f"\nTrying to validate {xml_file} using {schema_file}")
    try:
        schema = etree.XMLSchema(file=schema_file)
        xmlparser = etree.XMLParser(schema=schema)
        etree.parse(xml_file, xmlparser)
        print("Successfully validated")
    except Exception as err:
        print("Failed to validate")
        print(err)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_folder")
    parser.add_argument("schema_folder")
    args = parser.parse_args()

    conf_path = Path(args.config_folder)
    schema_path = Path(args.schema_folder)

    print_and_log(f"Configuration folder: {conf_path}")
    print_and_log(f"Schema folder: {schema_path}")

    validate(schema_path / "blocks.xsd", conf_path / "blocks.xml")
    validate(schema_path / "groups.xsd", conf_path / "groups.xml")
    validate(schema_path / "components.xsd", conf_path / "components.xml")
    validate(schema_path / "iocs.xsd", conf_path / "iocs.xml")
