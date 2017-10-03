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

    def add(self, path):
        """ Add a file to the repository
        Args:
            path (str): the file to add
        """
        if self._should_ignore(path):
            return
        if not self._needs_adding(path):
            print_and_log("GIT: unchanged, ignored or already added '{}'".format(path))
            return # unchanged, ignored or already added
        print_and_log("GIT: adding '{}' ".format(path))
        attempts = 0
        # note that index.add() does not honour .gitignore and passing force=False doesn't change this
        # however repo.untracked_files does honour .gitignore so use of self._needs_adding() above covers this
        while attempts < RETRY_MAX_ATTEMPTS:
            try:
                self.repo.index.add([path])
                return
            except WindowsError as err:
                # Most likely access denied, so try changing permissions then retry once
                try:
                    self._set_permissions()
                    self.repo.index.add([path])
                    return
                except Exception as err:
                    sleep(RETRY_INTERVAL)
            except Exception as err:
                sleep(RETRY_INTERVAL)

            attempts += 1

        raise AddToVersionControlException("Couldn't add to version control")

    def commit(self, commit_comment):
        """ Commit changes to a repository
        Args:
            commit_comment (str): comment to leave with the commit
        """
        if len(self.repo.index.diff("HEAD")) == 0:
            print_and_log("GIT: Nothing to commit")
            return # nothing staged for commit
        attempts = 0
        while attempts < RETRY_MAX_ATTEMPTS:
            try:
                self.repo.index.commit(commit_comment)
                if not self._is_local:
                    with self._push_lock:
                        self._push_required = True
                return
            except Exception as err:
                sleep(RETRY_INTERVAL)

            attempts += 1

        raise CommitToVersionControlException("Couldn't commit to version control")

    def update(self):
        """ reverts folder to the remote repository
        """
        try:
            if not self._is_local:
                self._pull()
            if self.repo.is_dirty():
                self.repo.index.checkout()
        except Exception as err:
            raise UpdateFromVersionControlException(err.message)

    def remove(self, path):
        """ Deletes file from the filesystem as well as removing from the repo
        Args:
            path (str): pat
        """
        try:
            if self._should_ignore(path) and os.path.exists(path):
                # the git library throws if we try to delete something that wasn't added
                # but we still have to delete the file from file system
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                return

            delete_list = []
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path, topdown=False):
                    for f in files:
                        delete_list.append(os.path.abspath(os.path.join(root, f)))
                    for d in dirs:
                        delete_list.append(os.path.abspath(os.path.join(root, d)))
            else:
                delete_list.append(path)
            self.repo.index.remove(delete_list, True)
        except Exception as err:
            raise RemoveFromVersionControlException(err.message)

    def _set_permissions(self):
        git_path = self.repo.git_dir
        os.chmod(git_path, stat.S_IWRITE)
        for root, dirs, files in os.walk(git_path):
            for d in dirs:
                os.chmod(os.path.join(root, d), stat.S_IWRITE)
            for f in files:
                os.chmod(os.path.join(root, f), stat.S_IWRITE)

    def _commit_and_push(self):
        push_interval = PUSH_BASE_INTERVAL
        first_failure = True

        while True:
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

    def _should_ignore(self, file_path):
        # Ignore anything that starts with the system tests prefix
        # (unfortunately putting the system test prefix in the .gitignore doesn't work
        # because the git library always forces an add - it has a force flag, but it's not used)
        # NOTE: this may now have been fixed by the new self._needs_adding() function
        # as repo.untracked_files does honour .gitignore
        return SYSTEM_TEST_PREFIX in file_path

    def add_all_edited_files(self):
        """
        Does a 'git add -u' which adds all edited files.
        """
        self.repo.git.add(u=True)

    def _needs_adding(self, path):
        """
        Check if file or directory really needs to be added to git
        """
        # we need to make sure paths we compare are consistent in both case and path separators
        # also as git returns changed/untracked files and we may get passed a directory name, we need
        # to use "startswith" on the directory prefix later so also make sure it ends with a separator
        # repo.untracked_files honours .gitignore allowing us to workaround the index.add() issue
        isdir = os.path.isdir(path)
        relpath = os.path.normcase(os.path.normpath(os.path.relpath(path, str(self.repo.working_dir))))
        if isdir and not relpath.endswith(os.sep):
            relpath = relpath + os.sep
        c1 = [ item.a_path for item in self.repo.index.diff(None) ]
        changed = [ os.path.normcase(os.path.normpath(str(p))) for p in c1 ]
        untracked = [ os.path.normcase(os.path.normpath(str(p))) for p in self.repo.untracked_files ]
        if isdir:
            # only add directory if it contains some changed/untracked files
            return any(p.startswith(relpath) for p in untracked + changed)
        else:
            return relpath in untracked + changed
