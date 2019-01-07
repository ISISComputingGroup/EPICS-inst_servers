import unittest
from server_common.loggers.isis_logger import create_xml_string


class TestISISLogger(unittest.TestCase):
    def test_WHEN_message_contains_invalid_unicode_THEN_xml_contains_string_repr(self):
        message = u"\u0002"

        xml_string = create_xml_string(message, "INFO", "BS")

        self.assertIn(r"'\x02'", xml_string)
        self.assertNotIn(message, xml_string)

    def test_WHEN_message_contains_valid_unicode_THEN_xml_contains_unicode(self):
        message = u"\t"

        xml_string = create_xml_string(message, "INFO", "BS")

        self.assertNotIn(r"'\x09'", xml_string)
        self.assertIn(message, xml_string)