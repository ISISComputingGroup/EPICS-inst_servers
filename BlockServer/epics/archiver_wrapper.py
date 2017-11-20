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

from __future__ import absolute_import
try:
    import urllib2 as urllib
except:
    # Use Python3 library
    import urllib.request as urllib


class ArchiverWrapper(object):
    def restart_archiver(self):
        # Set to ignore proxy for localhost
        proxy_handler = urllib.ProxyHandler({})
        opener = urllib.build_opener(proxy_handler)
        urllib.install_opener(opener)
        res = urllib.urlopen("http://localhost:4813/restart")
        d = res.read()
