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
import socket
from functools import wraps
from git import *
from threading import Thread, RLock
from time import sleep

from ConfigVersionControl.git_message_provider import GitMessageProvider
from ConfigVersionControl.version_control_exceptions import NotUnderVersionControl, NotUnderAllowedBranchException
from server_common.utilities import print_and_log, retry
from server_common.common_exceptions import MaxAttemptsExceededException

SYSTEM_TEST_PREFIX = "rcptt_"
ERROR_PREFIX = "Unable to commit to version control"
PUSH_RETRY_INTERVAL = 10
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


def check_branch_allowed(func):
    """
    Decorator which only runs the function if the branch is allowed
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.branch_allowed(str(self.repo.active_branch)):
            func(self, *args, **kwargs)
        else:
            raise NotUnderAllowedBranchException(f"Access to branch {self.repo.active_branch} is not allowed")
    return wrapper


class GitVersionControl:
    """Version Control class for dealing with git file operations"""
    def __init__(self, working_directory, repo, repo_name, push_interval, is_local=False):
        self._wd = working_directory
        self.repo = repo
        self._is_local = is_local
        self._repo_name = repo_name
        self._message_provider = GitMessageProvider()
        self.push_interval = push_interval

        if not is_local:
            self.remote = self.repo.remotes.origin

        self._push_lock = RLock()

    @staticmethod
    def branch_allowed(branch_name):
        """
        Checks that the branch is allowed to be pushed

        Args:
            branch_name (string): The name of the current branch
        Returns:
            bool : Whether the branch is allowed
        """
        # Only automatically push branches named after your instrument
        return branch_name.lower() == socket.gethostname().lower()

    def setup(self):
        """ Call when first starting the version control.
        Do startup actions here rather than in constructor to allow for easier testing
        """
        try:
            self._unlock()
        except MaxAttemptsExceededException:
            print_and_log("Unable to remove lock from version control repository, maximum tries exceeded", "MINOR")

        config_writer = self.repo.config_writer()
        # Set git repository to ignore file permissions otherwise will reset to read only
        config_writer.set_value("core", "filemode", False)

        # Start a background thread for pushing
        push_thread = Thread(target=self._commit_and_push, args=())
        push_thread.daemon = True  # Daemonise thread
        push_thread.start()

    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, OSError)
    def _unlock(self):
        """ Removes index.lock if it exists, and it's not being used
        """
        lock_file_path = os.path.join(self.repo.git_dir, "index.lock")
        if os.path.exists(lock_file_path):
            print_and_log(f"Found lock for version control repository, trying to remove: {lock_file_path}")
            os.remove(lock_file_path)
            print_and_log("Lock removed from version control repository")

    @check_branch_allowed
    @retry(RETRY_MAX_ATTEMPTS, RETRY_INTERVAL, GitCommandError)
    def _commit(self):
        """ Commit changes to a repository
        """
        num_files_changed = len(self.repo.index.diff("HEAD"))
        if num_files_changed == 0:
            return  # nothing staged for commit

        commit_comment = self._message_provider.get_commit_message(self.repo.index.diff("HEAD"))
        self.repo.index.commit(commit_comment)
        print_and_log(f"GIT: Committed {num_files_changed} changes")

    def _commit_and_push(self):
        """ Frequently adds, commits and pushes all file currently in the repository. """
        push_interval = self.push_interval
        first_failure = True

        while True:
            with self._push_lock:
                try:
                    self._add_all_files()
                    self._commit()
                    self.remote.push()
                    push_interval = self.push_interval
                    first_failure = True

                except MaxAttemptsExceededException:
                    print_and_log(f"{ERROR_PREFIX} for {self._repo_name}, maximum tries exceeded.")

                except GitCommandError as e:
                    # Most likely issue connecting to server, increase timeout, notify if it's the first time
                    push_interval = PUSH_RETRY_INTERVAL
                    if first_failure:
                        print_and_log(f"{ERROR_PREFIX} for {self._repo_name}, will retry in {PUSH_RETRY_INTERVAL} seconds", "MINOR")
                        first_failure = False
                except NotUnderAllowedBranchException as e:
                    print_and_log(f"{ERROR_PREFIX} for {self._repo_name}, {e.message}")

            sleep(push_interval)

    @check_branch_allowed
    def _add_all_files(self):
        """
        Does a 'git add -A' which adds all files in the repository.
        """
        self.repo.git.add(A=True)
