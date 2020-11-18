import unittest
from server_common.utilities import compress_and_hex
from hamcrest import *
import binascii
import zlib


class TestUtilities(unittest.TestCase):
    def test_GIVEN_unicode_string_WHEN_compressing_and_hexing_THEN_output_is_compressed_and_hexed_correctly(self):
        test = b"test"
        value = compress_and_hex(test)
        expected_value = binascii.hexlify(zlib.compress(test))
        assert_that(value, is_(expected_value))

    def test_GIVEN_string_WHEN_compressing_and_hexing_THEN_output_is_compressed_and_hexed_correctly(self):
        test = "test"
        value = compress_and_hex(test)
        expected_value = binascii.hexlify(bytes(test))
        assert_that(value, is_(expected_value))
