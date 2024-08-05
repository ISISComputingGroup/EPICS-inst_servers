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

import os
import shutil

from ConfigVersionControl.version_control_exceptions import (
    AddToVersionControlException,
    CommitToVersionControlException,
    RemoveFromVersionControlException,
    UpdateFromVersionControlException,
)


class MockVersionControl:
    def add(self, file_path):
        pass

    def add_all_edited_files(self):
        pass

    def remove(self, file_path):
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        elif os.path.isfile(file_path):
            os.remove(file_path)

    def commit(self, commit_comment):
        pass

    def update(self, update_path=""):
        pass


class FailOnAddMockVersionControl(MockVersionControl):
    def add(self, file_path):
        raise AddToVersionControlException("Oops cannot add")


class FailOnCommitMockVersionControl(MockVersionControl):
    def commit(self, commit_comment):
        raise CommitToVersionControlException("Oops cannot commit")


class FailOnRemoveMockVersionControl(MockVersionControl):
    def remove(self, file_path):
        raise RemoveFromVersionControlException("Oops cannot remove")


class FailOnUpdateMockVersionControl(MockVersionControl):
    def update(self, update_path=""):
        raise UpdateFromVersionControlException("Oops cannot update")
