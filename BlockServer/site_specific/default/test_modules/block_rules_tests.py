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

import re
import unittest

from BlockServer.mocks.mock_block_server import MockBlockServer
from BlockServer.site_specific.default.block_rules import BlockRules


class TestBlockRulesSequence(unittest.TestCase):
    """Unit tests for block rules, note that changes here may have to be propagated to clients"""

    def setUp(self):
        self.bs = MockBlockServer()
        self.block_rules = BlockRules(self.bs)

    def get_regex(self):
        regex_string = self.block_rules.rules["regex"]
        return re.compile(regex_string)

    def test_disallowed_in_json(self):
        self.assertTrue("disallowed" in self.block_rules.rules)
        disallowed_list = self.block_rules.rules["disallowed"]
        self.assertTrue(isinstance(disallowed_list, list))

    def test_regex_in_json(self):
        self.assertTrue("regex" in self.block_rules.rules)

    def test_regex_message_in_json(self):
        self.assertTrue("regexMessage" in self.block_rules.rules)

    def test_regex_lowercase_valid(self):
        self.assertTrue(self.get_regex().match("abc"))

    def test_regex_underscore_valid(self):
        self.assertTrue(self.get_regex().match("abc_"))

    def test_regex_uppercase_valid(self):
        regex = self.get_regex()
        self.assertTrue(regex.match("ABC"))

    def test_regex_numbers_valid(self):
        self.assertTrue(self.get_regex().match("abc1"))

    def test_regex_start_with_number_invalid(self):
        self.assertFalse(self.get_regex().match("1abc"))

    def test_regex_start_with_underscore_invalid(self):
        self.assertFalse(self.get_regex().match("_abc"))

    def test_regex_blank_invalid(self):
        self.assertFalse(self.get_regex().match(""))

    def test_regex_special_chars_invalid(self):
        self.assertFalse(self.get_regex().match("abc@"))
