import binascii
import unittest
import zlib
from hamcrest import *
from server_common.utilities import compress_and_hex


class TestUtilities(unittest.TestCase):
    def test_GIVEN_bytes_WHEN_compressing_and_hexing_THEN_output_is_compressed_and_hexed_correctly(self):
        test = b"test"
        value = compress_and_hex(test)
        expected_value = binascii.hexlify(zlib.compress(test))
        assert_that(value, is_(expected_value))

    def test_GIVEN_string_WHEN_compressing_and_hexing_THEN_output_is_compressed_and_hexed_correctly(self):
        test = "test"
        value = compress_and_hex(test)
        expected_value = binascii.hexlify(bytes(test, encoding="utf-8"))
        assert_that(value, is_(expected_value))
