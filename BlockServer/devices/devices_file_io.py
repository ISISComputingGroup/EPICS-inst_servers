import os
from xml.dom import minidom

from server_common.common_exceptions import MaxAttemptsExceededException
from server_common.utilities import retry

RETRY_MAX_ATTEMPTS = 20
RETRY_INTERVAL = 0.5


class DevicesFileIO:
    """Responsible for loading and saving the devices file."""

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, (OSError, IOError))
    def load_devices_file(self, file_name: str):
        """Load the devices file.

        Args:
            file_name: the devices file (full path)

        Returns:
            the XML as bytes
        """

        if not os.path.exists(file_name):
            # Break retry loop if file does not exist.
            raise MaxAttemptsExceededException
        with open(file_name, 'rb') as devfile:
            data = devfile.read()
            return data

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, (OSError, IOError))
    def save_devices_file(self, file_name: str, data: bytes):
        """Saves the devices info.

        Args:
            file_name: the devices file (full path)
            data: the xml to save
        """
        # If save file already exists remove first to avoid case issues
        if os.path.exists(file_name):
            os.remove(file_name)

        # Save the data
        with open(file_name, 'w') as devfile:
            pretty_xml = minidom.parseString(data).toprettyxml()
            devfile.write(pretty_xml)
