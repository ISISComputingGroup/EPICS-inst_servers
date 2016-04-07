import os
from server_common.utilities import print_and_log, compress_and_hex
from BlockServer.core.file_path_manager import FILEPATH_MANAGER

GET_SCREENS = "GET_SCREENS"
SET_SCREENS = "SET_SCREENS"

TEST_DATA = """<?xml version="1.0" ?>
<DeviceScreens xmlns:xi="http://www.w3.org/2001/XInclude">
    <devices>
        <device>
            <name>Eurotherm 1</name>
            <key>Eurotherm</key>
            <type>OPI</type>
            <properties>
                <property>
                    <key>EURO</key>
                    <value>EUROTHERM1</value>
                </property>
            </properties>
        </device>
    </devices>
</DeviceScreens>"""

SCREENS_FILE = "screens.xml"

class DevicesManager(object):
    """Class for managing the PVs associated with devices"""
    def __init__(self, block_server, cas, schema_folder, vc_manager):
        """Constructor.

        Args:
            block_server (BlockServer): A reference to the BlockServer instance.
            cas (CAServer): The channel access server for creating PVs on-the-fly
            schema_folder (string): The filepath for the devices schema
            vc_manager (ConfigVersionControl): The manager to allow version control modifications
        """
        self._directory = FILEPATH_MANAGER.config_dir
        self._schema_folder = schema_folder
        self._cas = cas
        self._devices_pvs = dict()
        self._vc = vc_manager
        self._bs = block_server
        self._current_config_file = ""

    def load_current(self):
        """Create the PVs for all the devices found in the devices directory."""
        devices_file_name = self.get_devices_filename()

        # Load the data, checking the schema
        try:
            with open(devices_file_name, 'r') as devfile:
                data = devfile.read()
                # ConfigurationSchemaChecker.check_device_matches_schema(
                #     os.path.join(self._schema_folder, SYNOPTIC_SCHEMA),
                #     data)
            # Get the device name
            self._create_pv(data)

            self._add_to_version_control(devices_file_name[0:-4])
        except Exception as err:
            print_and_log("Error creating device PV: %s" % str(err), "MAJOR")

        self._vc.commit("Blockserver started, devices updated")

    def _create_pv(self, data):
        """Creates a single PV based on a name and data.

        Args:
            data (string): Starting data for the pv, the pv name is derived from the name tag of this
        """

        # Create the PV
        self._cas.updatePV(GET_SCREENS, compress_and_hex(data))

    def get_devices_filename(self):
        """Gets the names of the synoptic files in the synoptics directory. Without the .xml extension.

        Returns:
            string : Current devices file name. Returns empty string if the file does not exist.
        """
        if not os.path.exists(self._current_config_file):
            print_and_log("Current devices file does not exist")
            return ""
        return self._current_config_file

    def set_current_config_file(self, current_config_dir):
        """Sets the names of the current configuration file.

        Args:
            current_config_dir (string): The name of the current configuration file.
        """

        self._current_config_file = os.path.join(current_config_dir, SCREENS_FILE)