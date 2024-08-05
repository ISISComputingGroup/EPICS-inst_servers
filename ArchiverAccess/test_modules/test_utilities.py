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

from unittest import TestCase

from hamcrest import *

from ArchiverAccess.utilities import add_default_field, truncate


class TestUtilities(TestCase):

    def test_GIVEN_pv_no_default_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = ""
        pv = "pv:name"
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_default_is_none_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = None
        pv = "pv:name"
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_is_none_and_default_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = "VAL"
        pv = None
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_is_blank_and_default_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = "VAL"
        pv = ""
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_has_field_and_default_WHEN_pv_with_default_THEN_pv_as_is(self):
        default_field = "VAL"
        pv = "pv.field"
        expected_pv = pv

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_pv_no_field_and_default_WHEN_pv_with_default_THEN_pv_has_field_with_dot(self):
        default_field = "VAL"
        pv = "pv"
        expected_pv = pv + "." + default_field

        result = add_default_field(pv, default_field)

        assert_that(result, is_(expected_pv))

    def test_GIVEN_number_WHEN_trancate_to_1_dp_THEN_number_is_truncated(self):
        num = 0.1234
        dps = 1
        expected_num = 0.1

        result = truncate(num, dps)

        assert_that(result, is_(expected_num))

    def test_GIVEN_number_WHEN_truncate_to_mre_dps_than_given_THEN_number_is_not_truncated(self):
        num = 0.12
        dps = 4
        expected_num = num

        result = truncate(num, dps)

        assert_that(result, is_(expected_num))

    def test_GIVEN_number_WHEN_trancate_to_0_dp_THEN_number_is_truncated(self):
        num = 123.12
        dps = 0
        expected_num = 123

        result = truncate(num, dps)

        assert_that(result, is_(expected_num))

    def test_GIVEN_number_WHEN_truncate_to_nearest_10_THEN_number_is_truncated(self):
        num = 123.12
        dps = -1
        expected_num = 120

        result = truncate(num, dps)

        assert_that(result, is_(expected_num))

    def test_GIVEN_number_WHEN_truncated_to_number_bigger_than_input_THEN_number_0(self):
        num = 123.12
        dps = -4
        expected_num = 0

        result = truncate(num, dps)

        assert_that(result, is_(expected_num))

    def test_GIVEN_int_number_WHEN_truncate_to_nearest_10_THEN_number_is_truncated(self):
        num = 250000
        dps = -5
        expected_num = 200000

        result = truncate(num, dps)

        assert_that(result, is_(expected_num))
