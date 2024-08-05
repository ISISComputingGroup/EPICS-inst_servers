from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from server_common.utilities import char_waveform


class PvNames(object):
    INSTRUMENT = "INSTRUMENT"


STATIC_PV_DATABASE = {
    PvNames.INSTRUMENT: char_waveform(50),
}
