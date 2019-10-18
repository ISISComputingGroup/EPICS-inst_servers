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

import datetime
import socket
from lxml import etree
import re

IOCLOG_ADDR = ("127.0.0.1", 7004)
_illegal_xml_chars_RE = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')


def escape_xml_illegal_chars(text):
    """Escapes illegal XML unicode characters to their python representation.
    See https://www.w3.org/TR/xml/#charsets
    Args:
        text (str): The text to escape.
    Returns:
        str: The corrected string.
    """
    return _illegal_xml_chars_RE.sub(lambda match: repr(match.group(0)), text)


def create_xml_string(message, severity, src):
    """Creates the xml string to send to the server.

    Args:
        message (string): The message to write.
        severity (string): Gives the severity of the message. Expected severities are MAJOR, MINOR and INFO.
        src (string): Gives the source of the message
    """
    msg_time = datetime.datetime.utcnow()
    msg_time_str = msg_time.isoformat()
    if msg_time.utcoffset() is None:
        msg_time_str += "Z"

    xml_message = etree.Element("message")
    etree.SubElement(xml_message, "clientName").text = src
    etree.SubElement(xml_message, "severity").text = severity
    etree.SubElement(xml_message, "contents").text = etree.CDATA(escape_xml_illegal_chars(message))
    etree.SubElement(xml_message, "type").text = "ioclog"
    etree.SubElement(xml_message, "eventTime").text = msg_time_str

    return etree.tostring(xml_message, encoding="utf-8")


class IsisLogger(object):
    def write_to_log(self, message, severity="INFO", src="BLOCKSVR"):
        """Writes a message to the IOC log. It is preferable to use print_and_log for easier debugging.
        Args:
            message (string): The message to write.
            severity (string, optional): Gives the severity of the message. Expected severities are MAJOR, MINOR and INFO.
                                        Default severity is INFO
            src (string, optional): Gives the source of the message. Default source is BLOCKSVR
        """
        if severity not in ['INFO', 'MINOR', 'MAJOR', 'FATAL']:
            print("write_to_ioc_log: invalid severity ", severity)
            return

        xml_string = create_xml_string(message, severity, src)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(IOCLOG_ADDR)
            sock.sendall(xml_string)
        except Exception as err:
            print("Could not send message to IOC log: %s" % err)
        finally:
            if sock is not None:
                sock.close()
