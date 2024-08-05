"""
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
"""

import datetime
import os
import time
import xml.etree.ElementTree as eTree
from shutil import copyfile
from subprocess import PIPE, STDOUT, run
from sys import platform
from xml.dom import minidom

from BlockServer.epics.archiver_wrapper import ArchiverWrapper
from server_common.utilities import print_and_log


class ArchiverManager:
    """This class is responsible for updating the EPICS Archiver that is responsible for logging the blocks."""

    RUN_CONTROL_PVS = ["LOW", "HIGH", "INRANGE", "ENABLE"]

    def __init__(self, uploader_path, settings_path, archiver=ArchiverWrapper()):
        """Constructor.

        Args:
            uploader_path (string): The filepath for the program that uploads the archiver settings.
            settings_path (string): The filepath for the settings to be writen to.
            archiver (ArchiverWrapper): The instance used to access the Archiver.
        """
        self._uploader_path = uploader_path
        self._settings_path = settings_path
        self._archive_wrapper = archiver

    def update_archiver(
        self, block_prefix, blocks, configuration_wants_to_use_own_block_config_xml, config_dir
    ):
        """Update the archiver to log the blocks specified.

        Args:
            block_prefix (string): The block prefix
            blocks (list): The blocks to archive
            configuration_wants_to_use_own_block_config_xml (bool): True if the configuration
                claims it contains the block_config.xml
            config_dir (str): The directory of the current configuration.
        """
        try:
            if self._settings_path is not None:
                self._if_config_contains_archiver_xml_then_copy_archive_config_else_generate_archive_config(
                    config_dir,
                    configuration_wants_to_use_own_block_config_xml,
                    block_prefix,
                    blocks,
                )
            if self._uploader_path is not None:
                self._upload_archive_config_then_wait_1_second_then_restart_archiver()
        except Exception as err:
            print_and_log(f"Could not update archiver: {err}", "MAJOR")

    def _upload_archive_config_then_wait_1_second_then_restart_archiver(self):
        """
        Upload the archive config, then wait 1 second, then restart the archiver.
        """
        self._upload_archive_config()
        # Needs a second delay
        print_and_log("Arbitrary wait after running archive settings uploader")
        time.sleep(1)
        print_and_log("Finished arbitrary wait")
        self._archive_wrapper.restart_archiver()

    def _if_config_contains_archiver_xml_then_copy_archive_config_else_generate_archive_config(
        self, config_dir, configuration_wants_to_use_own_block_config_xml, block_prefix, blocks
    ):
        """
        If the configuration contains the block_config.xml file and configuration_wants_to_use_own_block_config_xml
         is true then copy the xml file across.
         Otherwise, generate the config xml.

        Args:
            config_dir (str): The directory that contains the block_config.xml file.
            configuration_wants_to_use_own_block_config_xml (bool): Whether the configuration is set to use the block_config.xml file.
            block_prefix (str): The prefix to prefix blocks PV addresses with.
            blocks (List[Block]): The blocks to create the archive config with.
        """
        block_config_xml_file = os.path.join(config_dir, "block_config.xml")
        if configuration_wants_to_use_own_block_config_xml and os.path.exists(
            block_config_xml_file
        ):
            print_and_log("Using {} to configure block archiver".format(block_config_xml_file))
            copyfile(block_config_xml_file, self._settings_path)
        elif configuration_wants_to_use_own_block_config_xml:
            print_and_log(
                "Could not find {} generating archive config".format(block_config_xml_file)
            )
            self._generate_archive_config(block_prefix, blocks)
        else:
            self._generate_archive_config(block_prefix, blocks)

    def _generate_archive_config(self, block_prefix, blocks):
        print_and_log(f"Generating archiver configuration file: {self._settings_path}")
        root = eTree.Element("engineconfig")
        group = eTree.SubElement(root, "group")
        name = eTree.SubElement(group, "name")
        name.text = "BLOCKS"
        dataweb = eTree.SubElement(root, "group")
        dataweb_name = eTree.SubElement(dataweb, "name")
        dataweb_name.text = "DATAWEB"
        for block in blocks:
            # Append prefix for the archiver
            self._generate_archive_channel(group, block_prefix, block, dataweb)

        with open(self._settings_path, "w") as f:
            xml = minidom.parseString(eTree.tostring(root)).toprettyxml()
            f.write(xml)

    def _upload_archive_config(self):
        extra_args = {}
        if platform == "win32":
            from subprocess import STARTF_USESHOWWINDOW, STARTUPINFO, SW_HIDE

            extra_args = {
                "startupinfo": STARTUPINFO(dwFlags=STARTF_USESHOWWINDOW, wShowWindow=SW_HIDE)
            }
        f = os.path.abspath(self._uploader_path)
        if os.path.isfile(f):
            print_and_log(f"Running archiver settings uploader: {f}")
            p = run(f, stdout=PIPE, stderr=STDOUT, **extra_args)
            print_and_log(p.stdout)
            if p.returncode != 0:
                print_and_log(
                    "Retrying as status {} returned from subproccess.run".format(p.returncode)
                )
                time.sleep(1)
                p = run(f, stdout=PIPE, stderr=STDOUT, **extra_args)
                print_and_log(p.stdout)
                ## this would throw a CalledProcessError exception, but may cause more harm than good at moment
                # p.check_returncode()
                ## for the moment just print an error like before, so rest of config change happens
                if p.returncode != 0:
                    print_and_log(
                        "Error {} returned from subproccess.run for {}".format(p.returncode, f)
                    )
            print_and_log(f"Finished running archiver settings uploader: {f}")
        else:
            print_and_log(
                f"Could not find specified archiver uploader batch file: {self._uploader_path}"
            )

    def _generate_archive_channel(self, group, block_prefix, block, dataweb):
        if not (block.log_periodic and block.log_rate == 0):
            # Blocks that are logged
            channel = eTree.SubElement(group, "channel")
            name = eTree.SubElement(channel, "name")
            name.text = block_prefix + block.name
            period = eTree.SubElement(channel, "period")
            if block.log_periodic:
                period.text = str(datetime.timedelta(seconds=block.log_rate))
                eTree.SubElement(channel, "scan")
            else:
                period.text = str(datetime.timedelta(seconds=1))
                monitor = eTree.SubElement(channel, "monitor")
                monitor.text = str(block.log_deadband)
        else:
            # Blocks that aren't logged, but are needed for the dataweb view
            self._add_block_to_dataweb(block_prefix, block, "", dataweb)

        for run_control_pv in ArchiverManager.RUN_CONTROL_PVS:
            suffix = f":RC:{run_control_pv}.VAL"
            self._add_block_to_dataweb(block_prefix, block, suffix, dataweb)

    def _add_block_to_dataweb(self, block_prefix, block, block_suffix, dataweb):
        channel = eTree.SubElement(dataweb, "channel")
        name = eTree.SubElement(channel, "name")
        name.text = block_prefix + block.name + block_suffix
        period = eTree.SubElement(channel, "period")
        period.text = str(datetime.timedelta(seconds=300))
        eTree.SubElement(channel, "scan")
