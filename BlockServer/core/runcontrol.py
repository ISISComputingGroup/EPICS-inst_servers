import os
from time import sleep

from server_common.channel_access import caget, caput
from BlockServer.core.constants import TAG_RC_LOW, TAG_RC_HIGH, TAG_RC_ENABLE, TAG_RC_OUT_LIST
from server_common.utilities import print_and_log


TAG_RC_DICT = {"LOW": TAG_RC_LOW, "HIGH": TAG_RC_HIGH, "ENABLE": TAG_RC_ENABLE}
RC_PV = "CS:IOC:RUNCTRL_01:DEVIOS:SysReset"
RUNCONTROL_SETTINGS = "/rc_settings.cmd"
AUTOSAVE_DIR = "/autosave/RUNCTRL_01/"
RUNCONTROL_IOC = "RUNCTRL_01"


class RunControlManager(object):
    """A class for taking care of setting up run-control.
    """
    def __init__(self, prefix, config_dir, var_dir, ioc_control):
        """Constructor.

        Args:
            prefix (string) : The instrument prefix
            config_dir (string) : The root of the configuration directory
            var_dir (string) : The root of the VAR directory
            ioc_control (IocControl) : The object for restarting the IOC
        """
        self._prefix = prefix
        self._settings_file = config_dir + RUNCONTROL_SETTINGS
        self._autosave_dir = var_dir + AUTOSAVE_DIR
        self._block_prefix = prefix + "CS:SB:"
        self._stored_settings = None
        self._ioc_control = ioc_control
        print "RUNCONTROL SETTINGS FILE: %s" % self._settings_file
        print "RUNCONTROL AUTOSAVE DIRECTORY: %s" % self._autosave_dir

    def update_runcontrol_blocks(self, blocks):
        """Update the run-control settings in the run-control IOC with the current blocks.

        Args:
            blocks (OrderedDict) : The blocks that are part of the current configuration
        """
        f = None
        try:
            f = open(self._settings_file, 'w')
            for bn, blk in blocks.iteritems():
                f.write('dbLoadRecords("$(RUNCONTROL)/db/runcontrol.db","P=$(MYPVPREFIX),PV=$(MYPVPREFIX)CS:SB:%s")\n'
                        % blk.name)
            # Need an extra blank line
            f.write("\n")
        except Exception as err:
            print err
        finally:
            if f is not None:
                f.close()

    def get_out_of_range_pvs(self):
        """Get a list of PVs that are currently out of range.

        This may include PVs that are not blocks, but have had run-control settings applied directly

        Returns:
            list : A list of PVs that are out of range
        """
        raw = caget(self._prefix + TAG_RC_OUT_LIST, True).strip()
        raw = raw.split(" ")
        if raw is not None and len(raw) > 0:
            ans = list()
            for i in raw:
                if len(i) > 0:
                    ans.append(i)
            return ans
        else:
            return []

    def get_current_settings(self, blocks):
        """ Returns the current run-control settings

        Returns:
            dict : The current run-control settings
        """
        settings = dict()
        for bn, blk in blocks.iteritems():
            low = caget(self._block_prefix + blk.name + TAG_RC_LOW)
            high = caget(self._block_prefix + blk.name + TAG_RC_HIGH)
            enable = caget(self._block_prefix + blk.name + TAG_RC_ENABLE)
            if enable == "YES":
                enable = True
            else:
                enable = False
            settings[blk.name] = {"LOW": low, "HIGH": high, "ENABLE": enable}
        return settings

    def restore_config_settings(self, blocks):
        """Restore run-control settings based on what is stored in a configuration.

        Args:
            blocks (OrderedDict) : The blocks for the configuration
        """
        for n, blk in blocks.iteritems():
            if blk.save_rc_settings:
                settings = dict()
                if blk.rc_enabled:
                    settings["ENABLE"] = 1
                else:
                    settings["ENABLE"] = 0
                if blk.rc_lowlimit is not None:
                    settings["LOW"] = blk.rc_lowlimit
                if blk.rc_highlimit is not None:
                    settings["HIGH"] = blk.rc_highlimit
                self._set_rc_values(blk.name, settings)

    def set_runcontrol_settings(self, data):
        """ Replaces the run-control settings with new values.

        Args:
            data (dict) : The new run-control settings to set (dictionary of dictionaries)
        """
        for bn, settings in data.iteritems():
            if settings is not None:
                self._set_rc_values(bn, settings)

    def _set_rc_values(self, bn, settings):
        for key, value in settings.iteritems():
            if key.upper() in TAG_RC_DICT.keys():
                try:
                    caput(self._block_prefix + bn + TAG_RC_DICT[key.upper()], value)
                except Exception as err:
                    print_and_log("Problem with setting runcontrol for %s: %s" % (bn, err))

    def wait_for_ioc_start(self):
        """Waits for the run-control IOC to start."""
        # TODO: Give up after a bit
        print_and_log("Waiting for runcontrol IOC to start")
        while True:
            sleep(2)
            # See if the IOC has restarted by looking for a standard PV
            try:
                ans = caget(self._prefix + RC_PV)
            except Exception as err:
                # Probably has timed out
                ans = None
            if ans is not None:
                print_and_log("Runcontrol IOC started")
                break

    def start_ioc(self):
        """Start the IOC."""
        try:
            self._ioc_control.start_ioc(RUNCONTROL_IOC)
        except Exception as err:
            print_and_log("Problem with starting the run-control IOC: %s" % str(err), "MAJOR")

    def restart_ioc(self, clear_autosave):
        """ Restarts the IOC.

        Args:
            clear_autosave (bool) : Whether to delete the autosave files first
        """
        if clear_autosave:
            print_and_log("Removing the run-control autosave files")
            self._clear_autosave_files()
        else:
            print_and_log("Reusing the existing run-control autosave files")

        try:
            self._ioc_control.restart_ioc(RUNCONTROL_IOC, force=True)
        except Exception as err:
            print_and_log("Problem with restarting the run-control IOC: %s" % str(err), "MAJOR")

    def _clear_autosave_files(self):
        for fname in os.listdir(self._autosave_dir):
            file_path = os.path.join(self._autosave_dir, fname)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as err:
                print_and_log("Problem deleting autosave files for the run-control IOC: %s" % str(err), "MAJOR")
