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
from typing import Dict, OrderedDict
from xml.dom import minidom

from BlockServer.config.metadata import MetaData
from server_common.utilities import *
from BlockServer.config.group import Group
from BlockServer.config.block import Block
from BlockServer.config.ioc import IOC
from BlockServer.core.constants import *
from BlockServer.core.macros import PVPREFIX_MACRO


KEY_NONE = GRP_NONE.lower()
TAG_ENABLED = 'enabled'

SCHEMA_PATH = "http://epics.isis.rl.ac.uk/schema/"
IOC_SCHEMA = "iocs/1.0"
BLOCK_SCHEMA = "blocks/1.0"
GROUP_SCHEMA = "groups/1.0"
COMPONENT_SCHEMA = "components/1.0"
BANNER_SCHEMA = "banner/1.0"

TAG_META = "meta"
TAG_DESC = "description"
TAG_SYNOPTIC = "synoptic"
TAG_PROTECTED = "isProtected"
TAG_CONFIGURES_BLOCK_GW_AND_ARCHIVER = "configuresBlockGWAndArchiver"

NS_TAG_BLOCK = 'blk'
NS_TAG_IOC = 'ioc'
NS_TAG_COMP = 'comp'
NS_TAG_GROUP = 'grp'
NS_TAG_BANNER = 'banner'

NAMESPACES = {
    NS_TAG_BLOCK: SCHEMA_PATH + BLOCK_SCHEMA,
    NS_TAG_IOC: SCHEMA_PATH + IOC_SCHEMA,
    NS_TAG_COMP: SCHEMA_PATH + COMPONENT_SCHEMA,
    NS_TAG_GROUP: SCHEMA_PATH + GROUP_SCHEMA,
    NS_TAG_BANNER: SCHEMA_PATH + BANNER_SCHEMA,
}


class ConfigurationXmlConverter:
    """Converts configuration data to and from XML.

    Consists of static methods only.
    """

    @staticmethod
    def blocks_to_xml(blocks: OrderedDict, macros: Dict):
        """ Generates an XML representation for a supplied dictionary of blocks.

        Args:
            blocks (OrderedDict): The blocks in a configuration or component
            macros (dict): The macros for the BlockServer

        Returns:
            string : The XML representation of the blocks in a configuration
        """
        root = ElementTree.Element(TAG_BLOCKS)
        root.attrib["xmlns"] = SCHEMA_PATH + BLOCK_SCHEMA
        root.attrib["xmlns:blk"] = SCHEMA_PATH + BLOCK_SCHEMA
        root.attrib["xmlns:xi"] = "http://www.w3.org/2001/XInclude"
        for name, block in blocks.items():
            # Don't save if in component
            if block.component is None or block.component is False:
                ConfigurationXmlConverter._block_to_xml(root, block, macros)

        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def groups_to_xml(groups: OrderedDict, include_none: bool = False) -> str:
        """ Generates an XML representation for a supplied dictionary of groups.

        Args:
            groups: The groups in a configuration or component
            include_none: Whether to include the NONE group

        Returns:
            The XML representation of the groups in a configuration
        """
        root = ElementTree.Element(TAG_GROUPS)
        root.attrib["xmlns"] = SCHEMA_PATH + GROUP_SCHEMA
        root.attrib["xmlns:grp"] = SCHEMA_PATH + GROUP_SCHEMA
        root.attrib["xmlns:xi"] = "http://www.w3.org/2001/XInclude"
        for name, group in groups.items():
            # Don't generate xml if in NONE or if it is empty
            if name != KEY_NONE and group.blocks is not None:
                ConfigurationXmlConverter._group_to_xml(root, group)

        # If we are adding the None group it should go at the end
        if include_none and KEY_NONE in groups.keys():
            ConfigurationXmlConverter._group_to_xml(root, groups[KEY_NONE])
        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def iocs_to_xml(iocs: OrderedDict):
        """ Generates an XML representation for a supplied list of iocs.

        Args:
            iocs: The IOCs in a configuration or component

        Returns:
            string : The XML representation of the IOCs in a configuration
        """
        root = ElementTree.Element(TAG_IOCS)
        root.attrib["xmlns"] = SCHEMA_PATH + IOC_SCHEMA
        root.attrib["xmlns:ioc"] = SCHEMA_PATH + IOC_SCHEMA
        root.attrib["xmlns:xi"] = "http://www.w3.org/2001/XInclude"
        for name in iocs.keys():
            # Don't save if in component
            if iocs[name].component is None:
                ConfigurationXmlConverter._ioc_to_xml(root, iocs[name])
        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def components_to_xml(comps: OrderedDict):
        """ Generates an XML representation for a supplied dictionary of components.

        Args:
            comps: The components in the configuration

        Returns:
            string : The XML representation of the components in a configuration
        """
        root = ElementTree.Element(TAG_COMPONENTS)
        root.attrib["xmlns"] = SCHEMA_PATH + COMPONENT_SCHEMA
        root.attrib["xmlns:comp"] = SCHEMA_PATH + COMPONENT_SCHEMA
        root.attrib["xmlns:xi"] = "http://www.w3.org/2001/XInclude"
        for name, case_sensitve_name in comps.items():
            ConfigurationXmlConverter._component_to_xml(root, case_sensitve_name)
        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def meta_to_xml(data: MetaData):
        """ Generates an XML representation of the meta data for each configuration.

        Args:
            data: The metadata to convert to XML

        Returns:
            string : The XML representation of the metadata in a configuration
        """
        root = ElementTree.Element(TAG_META)

        desc_xml = ElementTree.SubElement(root, TAG_DESC)
        desc_xml.text = data.description

        syn_xml = ElementTree.SubElement(root, TAG_SYNOPTIC)
        syn_xml.text = data.synoptic

        edits_xml = ElementTree.SubElement(root, TAG_EDITS)
        for e in data.history:
            edit = ElementTree.SubElement(edits_xml, TAG_EDIT)
            edit.text = e

        protect_xml = ElementTree.SubElement(root, TAG_PROTECTED)
        protect_xml.text = str(data.isProtected).lower()

        configure_block_gw_and_archiver_xml = ElementTree.SubElement(root, TAG_CONFIGURES_BLOCK_GW_AND_ARCHIVER)
        configure_block_gw_and_archiver_xml.text = str(data.configuresBlockGWAndArchiver).lower()

        return minidom.parseString(ElementTree.tostring(root)).toprettyxml()

    @staticmethod
    def _block_to_xml(root_xml: ElementTree.Element, block: Block, macros: Dict):
        """Generates the XML for a block"""
        name = block.name
        read_pv = block.pv
        local = block.local
        visible = block.visible

        block_xml = ElementTree.SubElement(root_xml, TAG_BLOCK)
        name_xml = ElementTree.SubElement(block_xml, TAG_NAME)
        name_xml.text = name
        pv_xml = ElementTree.SubElement(block_xml, TAG_READ_PV)

        # If it is local we strip off MYPVPREFIX
        if local:
            pre = macros[PVPREFIX_MACRO]
            pv_xml.text = read_pv.replace(pre, "")
        else:
            pv_xml.text = read_pv

        local_xml = ElementTree.SubElement(block_xml, TAG_LOCAL)
        local_xml.text = str(local)
        visible_xml = ElementTree.SubElement(block_xml, TAG_VISIBLE)
        visible_xml.text = str(visible)

        # Runcontrol
        enabled = ElementTree.SubElement(block_xml, TAG_RUNCONTROL_ENABLED)
        enabled.text = str(block.rc_enabled)
        if block.rc_lowlimit is not None:
            low = ElementTree.SubElement(block_xml, TAG_RUNCONTROL_LOW)
            low.text = str(block.rc_lowlimit)
        if block.rc_highlimit is not None:
            high = ElementTree.SubElement(block_xml, TAG_RUNCONTROL_HIGH)
            high.text = str(block.rc_highlimit)

        suspend_on_invalid = ElementTree.SubElement(block_xml, TAG_RUNCONTROL_SUSPEND_ON_INVALID)
        suspend_on_invalid.text = str(block.rc_suspend_on_invalid)

        # Logging
        log_periodic = ElementTree.SubElement(block_xml, TAG_LOG_PERIODIC)
        log_periodic.text = str(block.log_periodic)

        log_rate = ElementTree.SubElement(block_xml, TAG_LOG_RATE)
        log_rate.text = str(block.log_rate)

        log_deadband = ElementTree.SubElement(block_xml, TAG_LOG_DEADBAND)
        log_deadband.text = str(block.log_deadband)

    @staticmethod
    def _group_to_xml(root_xml: ElementTree, group: Group):
        """Generates the XML for a group"""
        grp = ElementTree.SubElement(root_xml, TAG_GROUP)
        grp.set(TAG_NAME, group.name)
        if group.component is not None:
            grp.set(TAG_COMPONENT, group.component)
        for blk in group.blocks:
            b = ElementTree.SubElement(grp, TAG_BLOCK)
            b.set(TAG_NAME, blk)

    @staticmethod
    def _ioc_to_xml(root_xml: ElementTree.Element, ioc: IOC):
        """Generates the XML for an ioc"""
        grp = ElementTree.SubElement(root_xml, TAG_IOC)
        grp.set(TAG_NAME, ioc.name)
        if ioc.autostart is not None:
            grp.set(TAG_AUTOSTART, str(ioc.autostart).lower())
        if ioc.restart is not None:
            grp.set(TAG_RESTART, str(ioc.restart).lower())
        if ioc.remotePvPrefix is not None:
            grp.set(TAG_REMOTE_PREFIX, str(ioc.remotePvPrefix))

        grp.set(TAG_SIMLEVEL, str(ioc.simlevel))

        # Add any macros
        value_list_to_xml(ioc.macros, grp, TAG_MACROS, TAG_MACRO)

        # Add any pvs
        value_list_to_xml(ioc.pvs, grp, TAG_PVS, TAG_PV)

        # Add any pvsets
        value_list_to_xml(ioc.pvsets, grp, TAG_PVSETS, TAG_PVSET)

    @staticmethod
    def _component_to_xml(root_xml: ElementTree.Element, name: str):
        """Generates the XML for a component"""
        grp = ElementTree.SubElement(root_xml, TAG_COMPONENT)
        grp.set(TAG_NAME, name)

    @staticmethod
    def blocks_from_xml(root_xml: ElementTree.Element, blocks: OrderedDict, groups: OrderedDict):
        """ Populates the supplied dictionary of blocks and groups based on an XML tree.

        Args:
            root_xml: The XML tree object
            blocks: The blocks dictionary to populate
            groups: The groups dictionary to populate with the blocks

        """
        # Get the blocks
        blks = ConfigurationXmlConverter._find_all_nodes(root_xml, NS_TAG_BLOCK, TAG_BLOCK)

        for b in blks:
            n = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_NAME)
            read = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_READ_PV)
            if n is not None and n.text != "" and read is not None and read.text is not None:
                name = n.text

                # Blocks automatically get assigned to the NONE group
                blocks[name.lower()] = Block(name, read.text)
                groups[KEY_NONE].blocks.append(name)

                # Check to see if not local
                loc = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_LOCAL)
                if loc is not None and loc.text == "False":
                    blocks[name.lower()].local = False

                # Check for visibility
                vis = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_VISIBLE)
                if vis is not None and vis.text == "False":
                    blocks[name.lower()].visible = False

                # Runcontrol
                rc_enabled = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_RUNCONTROL_ENABLED)
                if rc_enabled is not None:
                    blocks[name.lower()].rc_enabled = (rc_enabled.text == "True")

                rc_low = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_RUNCONTROL_LOW)
                if rc_low is not None:
                    blocks[name.lower()].rc_lowlimit = float(rc_low.text)
                rc_high = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_RUNCONTROL_HIGH)
                if rc_high is not None:
                    blocks[name.lower()].rc_highlimit = float(rc_high.text)

                rc_suspend_on_invalid = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_RUNCONTROL_SUSPEND_ON_INVALID)
                if rc_suspend_on_invalid is not None:
                    blocks[name.lower()].rc_suspend_on_invalid = (rc_suspend_on_invalid.text == "True")

                # Logging
                log_periodic = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_LOG_PERIODIC)
                if not (log_periodic is None):
                    blocks[name.lower()].log_periodic = (log_periodic.text == "True")

                log_rate = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_LOG_RATE)
                if not (log_rate is None):
                    blocks[name.lower()].log_rate = float(log_rate.text)

                log_deadband = ConfigurationXmlConverter._find_single_node(b, NS_TAG_BLOCK, TAG_LOG_DEADBAND)
                if not (log_deadband is None):
                    blocks[name.lower()].log_deadband = float(log_deadband.text)

    @staticmethod
    def groups_from_xml(root_xml: ElementTree.Element, groups: OrderedDict, blocks: OrderedDict):
        """ Populates the supplied dictionary of groups and assign blocks based on an XML tree

        Args:
            root_xml: The XML tree object
            blocks: The blocks dictionary
            groups: The groups dictionary to populate
        """
        # Get the groups
        grps = ConfigurationXmlConverter._find_all_nodes(root_xml, NS_TAG_GROUP, TAG_GROUP)
        for g in grps:
            gname = g.attrib[TAG_NAME]
            try:
                gcomp = g.attrib[TAG_COMPONENT]
            except KeyError:
                gcomp = None
            gname_low = gname.lower()

            # Add the group to the dict unless it already exists (i.e. the group is defined twice)
            if gname_low not in groups.keys():
                groups[gname_low] = Group(gname, gcomp)

            blks = ConfigurationXmlConverter._find_all_nodes(g, NS_TAG_GROUP, TAG_BLOCK)

            for b in blks:
                name = b.attrib[TAG_NAME]

                # Check block is not already in the group. Unlikely, but may be a config was edited by hand...
                if name not in groups[gname_low].blocks:
                    groups[gname_low].blocks.append(name)
                if name.lower() in blocks.keys():
                    blocks[name.lower()].group = gname

                # Remove the block from the NONE group
                if KEY_NONE in groups and name in groups[KEY_NONE].blocks:
                    groups[KEY_NONE].blocks.remove(name)

    @staticmethod
    def ioc_from_xml(root_xml: ElementTree.Element, iocs: OrderedDict):
        """ Populates the supplied dictionary of IOCs based on an XML tree.

        Args:
            root_xml: The XML tree object
            iocs: The IOCs dictionary
        """
        iocs_xml = ConfigurationXmlConverter._find_all_nodes(root_xml, NS_TAG_IOC, TAG_IOC)
        for i in iocs_xml:
            n = i.attrib[TAG_NAME]
            if n is not None and n != "":
                iocs[n.upper()] = IOC(n.upper())

                options = i.keys()
                if TAG_AUTOSTART in options:
                    iocs[n.upper()].autostart = parse_boolean(i.attrib[TAG_AUTOSTART])
                if TAG_RESTART in options:
                    iocs[n.upper()].restart = parse_boolean(i.attrib[TAG_RESTART])
                if TAG_SIMLEVEL in options:
                    level = i.attrib[TAG_SIMLEVEL].lower()
                    if level in SIMLEVELS:
                        iocs[n.upper()].simlevel = level
                if TAG_REMOTE_PREFIX in options:
                    iocs[n.upper()].remotePvPrefix = i.attrib[TAG_REMOTE_PREFIX]

                try:
                    # Get any macros
                    macros_xml = ConfigurationXmlConverter._find_single_node(i, NS_TAG_IOC, TAG_MACROS)
                    for m in macros_xml:
                        iocs[n.upper()].macros[m.attrib[TAG_NAME]] = {TAG_VALUE: str(m.attrib[TAG_VALUE])}
                    # Get any pvs
                    pvs_xml = ConfigurationXmlConverter._find_single_node(i, NS_TAG_IOC, TAG_PVS)
                    for p in pvs_xml:
                        iocs[n.upper()].pvs[p.attrib[TAG_NAME]] = {TAG_VALUE: str(p.attrib[TAG_VALUE])}
                    # Get any pvsets
                    pvsets_xml = ConfigurationXmlConverter._find_single_node(i, NS_TAG_IOC,  TAG_PVSETS)
                    for ps in pvsets_xml:
                        iocs[n.upper()].pvsets[ps.attrib[TAG_NAME]] = \
                            {TAG_ENABLED: parse_boolean(str(ps.attrib[TAG_ENABLED]))}
                except Exception as err:
                    raise Exception("Tag not found in ioc.xml (" + str(err) + ")")

    @staticmethod
    def components_from_xml(root_xml: ElementTree.Element, components: OrderedDict):
        """Populates the supplied dictionary of components based on an XML tree.

        Args:
            root_xml: The XML tree object
            components: The components dictionary
        """
        components_xml = ConfigurationXmlConverter._find_all_nodes(root_xml, NS_TAG_COMP, TAG_COMPONENT)
        for i in components_xml:
            n = i.attrib[TAG_NAME]
            if n is not None and n != "":
                components[n.lower()] = n

    @staticmethod
    def get_configuresBlockGWAndArchiver_from_xml(root_xml: ElementTree.Element) -> bool:
        configuresBlockGWAndArchiver = root_xml.find("./" + TAG_CONFIGURES_BLOCK_GW_AND_ARCHIVER)
        if configuresBlockGWAndArchiver is not None and configuresBlockGWAndArchiver.text is not None:
            return configuresBlockGWAndArchiver.text.lower() == "true"
        else:
            return False

    @staticmethod
    def meta_from_xml(root_xml: ElementTree.Element, data: MetaData):
        """Populates the supplied MetaData object based on an XML tree.

        Args:
            root_xml: The XML tree object
            data: The metadata object
        """
        description = root_xml.find("./" + TAG_DESC)
        if description is not None:
            data.description = description.text if description.text is not None else ""

        synoptic = root_xml.find("./" + TAG_SYNOPTIC)
        if synoptic is not None:
            data.synoptic = synoptic.text if synoptic.text is not None else ""

        isProtected = root_xml.find("./" + TAG_PROTECTED)
        if isProtected is not None:
            if isProtected.text is not None:
                data.isProtected = isProtected.text.lower() == "true"
            else:
                data.isProtected = False

        data.configuresBlockGWAndArchiver = ConfigurationXmlConverter.get_configuresBlockGWAndArchiver_from_xml(root_xml)

        edits = root_xml.findall("./" + TAG_EDITS + "/" + TAG_EDIT)
        data.history = [e.text for e in edits]

    @staticmethod
    def _find_all_nodes(root: ElementTree.Element, tag: str, name: str):
        """Finds all the nodes regardless of whether it has a namespace or not.

        For example the name space for IOCs is xmlns:ioc="http://epics.isis.rl.ac.uk/schema/iocs/1.0"

        Args:
            root: The XML tree object
            tag: The namespace tag
            name: The item we are looking for

        Returns: list of children
        """
        # First try with namespace
        nodes = root.findall(f'{tag}:{name}', NAMESPACES)
        if len(nodes) == 0:
            # Try without namespace
            nodes = root.findall(name)
        return nodes

    @staticmethod
    def _find_single_node(root: ElementTree.Element, tag: str, name: str) -> ElementTree.Element:
        """Finds a single node regardless of whether it has a namespace or not.

        For example the name space for IOCs is xmlns:ioc="http://epics.isis.rl.ac.uk/schema/iocs/1.0"

        Args:
            root: The XML tree object
            tag: The namespace tag
            name: The item we are looking for

        Returns: The found node
        """
        # First try with namespace
        node = root.find(f'{tag}:{name}', NAMESPACES)
        if node is None:
            # Try without namespace
            node = root.find(name)
        return node

    @staticmethod
    def _display(child, index):
        return {
                    "index": index,
                    "name": ConfigurationXmlConverter._find_single_node(child, "banner", "name").text,
                    "pv": ConfigurationXmlConverter._find_single_node(child, "banner", "pv").text,
                    "local": ConfigurationXmlConverter._find_single_node(child, "banner", "local").text,
                    "width": ConfigurationXmlConverter._find_single_node(child, "banner", "width").text,
               }

    @staticmethod
    def _button(child, index):
        return {
                    "index": index,
                    "name": ConfigurationXmlConverter._find_single_node(child, "banner", "name").text,
                    "pv": ConfigurationXmlConverter._find_single_node(child, "banner", "pv").text,
                    "local": ConfigurationXmlConverter._find_single_node(child, "banner", "local").text,
                    "pvValue": ConfigurationXmlConverter._find_single_node(child, "banner", "pvValue").text,
                    "textColour": ConfigurationXmlConverter._find_single_node(child, "banner", "textColour").text,
                    "buttonColour": ConfigurationXmlConverter._find_single_node(child, "banner", "buttonColour").text,
                    "fontSize": ConfigurationXmlConverter._find_single_node(child, "banner", "fontSize").text,
                    "width": ConfigurationXmlConverter._find_single_node(child, "banner", "width").text,
                    "height": ConfigurationXmlConverter._find_single_node(child, "banner", "height").text,
               }

    @staticmethod
    def banner_config_from_xml(root):
        """
        Parses the banner config XML to produce a banner config dictionary

        Args:
            root: The root XML node

        Returns:
            A dictionary with two entries, the banner items and the banner buttons.
            The items have the properties name, pv, local.
            The buttons have the properties name, pv, local, pvValue, textColour, buttonColour, width, height.
        """
        if root is None:
            return []

        banner_displays = []
        banner_buttons = []

        items = ConfigurationXmlConverter._find_single_node(root, "banner", "items")
        index = 0

        for item in items:
            child = item.find("./")
            if "display" in child.tag:
                banner_displays.append(ConfigurationXmlConverter._display(child, index))
            else:
                banner_buttons.append(ConfigurationXmlConverter._button(child, index))
            index += 1

        return {
            "items": banner_displays,
            "buttons": banner_buttons,
        }
