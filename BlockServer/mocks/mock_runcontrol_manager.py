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

from BlockServer.core.constants import TAG_RC_LOW, TAG_RC_HIGH, TAG_RC_ENABLE, TAG_RC_OUT_LIST


class MockBlock:
    def __init__(self):
        self.value = 0
        self.enable = False
        self.lowlimit = 0
        self.highlimit = 0


class MockRunControlManager:
    def __init__(self):
        self._prefix = ""
        self._block_prefix = ""
        self._stored_settings = None
        self.mock_blocks = dict()

    def update_runcontrol_blocks(self, blocks):
        for b, blk in blocks.items():
            self.mock_blocks[blk.name] = MockBlock()
            self.mock_blocks[blk.name].enable = blk.rc_enabled
            self.mock_blocks[blk.name].lowlimit = blk.rc_lowlimit
            self.mock_blocks[blk.name].highlimit = blk.rc_highlimit

    def get_out_of_range_pvs(self):
        raw = ""
        for n, blk in self.mock_blocks.items():
            if blk.enable:
                if blk.value < blk.lowlimit or blk.value > blk.highlimit:
                    raw += n + " "
        raw = raw.strip().split(" ")
        if raw is not None and len(raw) > 0:
            ans = list()
            for i in raw:
                if len(i) > 0:
                    ans.append(i)
            return ans
        else:
            return []

    def get_current_settings(self, blocks):
        # Blocks object is ignored for testing
        settings = dict()
        for bn, blk in self.mock_blocks.items():
            low = self.mock_blocks[bn].lowlimit
            high = self.mock_blocks[bn].highlimit
            enable = self.mock_blocks[bn].enable
            settings[bn] = {"LOW": low, "HIGH": high, "ENABLE": enable}
        return settings

    def restore_config_settings(self, blocks):
        for n, blk in blocks.items():
            settings = dict()
            if blk.rc_enabled:
                settings["ENABLE"] = True
            if blk.rc_lowlimit is not None:
                settings["LOW"] = blk.rc_lowlimit
            if blk.rc_highlimit is not None:
                settings["LOW"] = blk.rc_highlimit
            self.set_runcontrol_settings(settings)

    def set_runcontrol_settings(self, data):
        # Data should be a dictionary of dictionaries
        for bn, settings in data.items():
            if settings is not None and bn in self.mock_blocks.keys():
                self.mock_blocks[bn].enable = settings["ENABLE"]
                self.mock_blocks[bn].lowlimit = settings["LOW"]
                self.mock_blocks[bn].highlimit = settings["HIGH"]

    def wait_for_ioc_restart(self):
        pass

    def wait_for_ioc_start(self):
        pass

    def start_ioc(self):
        pass

    def restart_ioc(self, clear_autosave):
        pass
