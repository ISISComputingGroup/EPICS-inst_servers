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
import stat
import socket
from git import *
from version_control_exceptions import *
from threading import Thread, RLock
from time import sleep
from server_common.utilities import print_and_log

SYSTEM_TEST_PREFIX = "rcptt_"
GIT_REMOTE_LOCATION = 'http://control-svcs.isis.cclrc.ac.uk/gitroot/instconfigs/test.git'
PUSH_BASE_INTERVAL = 10
PUSH_RETRY_INTERVAL = 30
RETRY_INTERVAL = 0.1
RETRY_MAX_ATTEMPTS = 100


class RepoFactory:
    @staticmethod
    def get_repo(working_directory):
        # Check repo
        try:
            return Repo(working_directory, search_parent_directories=True)
        except Exception as e:
            # Not a valid repository
            raise NotUnderVersionControl(working_directory)


class GitVersionControl:
    """Version Control class for dealing with git file operations"""
    def __init__(self, working_directory, repo, is_local=False):
        self._wd = working_directory
        self.repo = repo
        self._is_local = is_local

        if not is_local:
            self.remote = self.repo.remotes.origin

        self._push_lock = RLock()

    def setup(self):
        """ Call when first starting the version control.
        Do startup actions here rather than in constructor to allow for easier testing
        """
        if not self.branch_allowed(str(self.repo.active_branch)):
            raise NotUnderAllowedBranchException("Access to branch %s not allowed" % self.repo.active_branch)

        try:
            self._unlock()
        except UnlockVersionControlException as err:
            raise err

        config_writer = self.repo.config_writer()
        # Set git repository to ignore file permissions otherwise will reset to read only
        config_writer.set_value("core", "filemode", False)
        self.add_all_files()

        # Start a background thread for pushing
        push_thread = Thread(target=self._commit_and_push, args=())
        push_thread.daemon = True  # Daemonise thread
        push_thread.start()

    @staticmethod
    def branch_allowed(branch_name):
        """Checks that the branch is allowed to be pushed

        Args:
            branch_name (string): The name of the current branch
        Returns:
            bool : Whether the branch is allowed
        """
        branch_name = branch_name.lower()

        if "master" in branch_name:
            return False

        if branch_name.startswith("nd") and branch_name != socket.gethostname().lower():
            # You're trying to push to a different instrument
            return False

        return True

    def _unlock(self):
        """ Removes index.lock if it exists, and it's not being used
        """
        attempts = 0
        while attempts < RETRY_MAX_ATTEMPTS:
            try:
                lock_file_path = os.path.join(self.repo.git_dir, "index.lock")
                if os.path.exists(lock_file_path):
                    print_and_log("Found lock for version control repository, trying to remove: %s" % lock_file_path,
                                  "INFO")
                    os.remove(lock_file_path)
                    print_and_log("Lock removed from version control repository", "INFO")

                return
            except:
                # Exception will be thrown below if the function doesn't return.
                sleep(RETRY_INTERVAL)

            attempts += 1

        raise UnlockVersionControlException("Unable to remove lock from version control repository.")

    def commit(self,):
        """ Commit changes to a repository
        """
        num_files_changed = len(self.repo.index.diff("HEAD"))
        if num_files_changed == 0:
            print_and_log("GIT: Nothing to commit")
            return  # nothing staged for commit
        attempts = 0
        while attempts < RETRY_MAX_ATTEMPTS:
            try:
                # TODO this could be more detailed
                commit_comment = "{changed} files modified/deleted".format(changed=num_files_changed)
                print_and_log("GIT: Committed {changed} changes".format(changed=num_files_changed))
                self.repo.index.commit(commit_comment)
                return
            except Exception as err:
                sleep(RETRY_INTERVAL)

            attempts += 1

        raise CommitToVersionControlException("Couldn't commit to version control")

    def _commit_and_push(self):
        push_interval = PUSH_BASE_INTERVAL
        first_failure = True

        while True:
            self.add_all_files()
            self.commit()
            with self._push_lock:
                    try:
                        self.remote.push()
                        push_interval = PUSH_BASE_INTERVAL
                        first_failure = True

                    except GitCommandError as e:
                        # Most likely issue connecting to server, increase timeout, notify if it's the first time
                        push_interval = PUSH_RETRY_INTERVAL
                        if first_failure:
                            print_and_log("Unable to push config changes, will retry in %i seconds"
                                          % PUSH_RETRY_INTERVAL, "MINOR")
                            first_failure = False

            sleep(push_interval)

    def add_all_files(self):
        """
        Does a 'git add -u' which adds all edited files.
        """
        self.repo.git.add(A=True)
