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
from xml.dom import minidom

from server_common.utilities import print_and_log, retry

RETRY_MAX_ATTEMPTS = 20
RETRY_INTERVAL = 0.5


class SynopticFileIO:

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, (OSError, IOError))
    def write_synoptic_file(self, name, save_path, xml_data):
        # If save file already exists remove first to avoid case issues
        if os.path.exists(save_path):
            os.remove(save_path)
        # Save the data
        with open(save_path, 'wb') as synfile:
            pretty_xml = minidom.parseString(xml_data).toprettyxml()
            # toprettyxml() returns a string so we have to convert it to bytes in order to write out as bytes
            synfile.write(bytes(pretty_xml, encoding="utf-8"))
            return

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, (OSError, IOError))
    def read_synoptic_file(self, directory, fullname):
        path = os.path.join(directory, fullname)

        with open(path, 'rb') as synfile:
            data = synfile.read()

        return data

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, (OSError, IOError))
    def delete_synoptic(self, directory, fullname):
        path = os.path.join(directory, fullname)

        if os.path.exists(path):
            os.remove(path)

    def get_list_synoptic_files(self, directory):
        if not os.path.exists(directory):
            print_and_log("Synoptics directory does not exist")
            return list()
        return [f for f in os.listdir(directory) if f.endswith(".xml")]
