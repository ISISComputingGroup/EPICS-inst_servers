from __future__ import print_function, absolute_import, division, unicode_literals
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

import json
import typing

import six
import unicodedata
import traceback

from server_common.channel_access import ChannelAccess
from server_common.mysql_abstraction_layer import SQLAbstraction
from server_common.utilities import compress_and_hex, char_waveform, print_and_log

from typing import Type, Union


class User(object):
    """
    A user class to allow for easier conversions from database to json.
    """
    def __init__(self, name: str = "UNKNOWN", institute: str = "UNKNOWN", role: str = "UNKNOWN"):
        self.name = name
        self.institute = institute
        self.role = role


class ExpDataSource(object):
    """
    This is a humble object containing all the code for accessing the database.
    """
    def __init__(self):
        self._db = SQLAbstraction('exp_data', "exp_data", "$exp_data")

    def get_team(self, experiment_id: str) -> list:
        """
        Gets the team members.

        Args:
            experiment_id: the id of the experiment to load related data from

        Returns:
            team: the team data found by the SQL query
        """
        try:
            sqlquery = "SELECT user.name, user.organisation, role.name"
            sqlquery += " FROM role, user, experimentteams"
            sqlquery += " WHERE role.roleID = experimentteams.roleID"
            sqlquery += " AND user.userID = experimentteams.userID"
            sqlquery += " AND experimentteams.experimentID = %s"
            sqlquery += " GROUP BY user.userID"
            sqlquery += " ORDER BY role.priority"
            team = [list(element) for element in self._db.query(sqlquery, (experiment_id,))]
            if len(team) == 0:
                raise ValueError("unable to find team details for experiment ID {}".format(experiment_id))
            else:
                return team
        except Exception:
            print_and_log(traceback.format_exc())
            return []

    def experiment_exists(self, experiment_id: str) -> bool:
        """
        Gets the experiment.

        Args:
            experiment_id: the id of the experiment to load related data from

        Returns:
            exists: TRUE if the experiment exists, FALSE otherwise
        """
        try:
            sqlquery = "SELECT experiment.experimentID"
            sqlquery += " FROM experiment "
            sqlquery += " WHERE experiment.experimentID = %s"
            id = self._db.query(sqlquery, (experiment_id,))
            return len(id) >= 1
        except Exception:
            print_and_log(traceback.format_exc())
            return False


class ExpData(object):
    """
    A wrapper to connect to the IOC database via MySQL.
    """
    EDPV = {
        'ED:RBNUMBER:SP': char_waveform(16000),
        'ED:USERNAME:SP': char_waveform(16000)
    }

    _to_ascii = {}

    def __init__(self, prefix: str,
                 db: Union[ExpDataSource, 'MockExpDataSource'],
                 ca: Union[ChannelAccess, 'MockChannelAccess'] = ChannelAccess()):
        """
        Constructor.

        Args:
            prefix: The pv prefix of the instrument the server is being run on
            db: The source of the experiment data
            ca: The channel access server to use
        """
        # Build the PV names to be used
        self._simrbpv = prefix + "ED:SIM:RBNUMBER"
        self._daerbpv = prefix + "ED:RBNUMBER:DAE:SP"
        self._simnames = prefix + "ED:SIM:USERNAME"
        self._daenamespv = prefix + "ED:USERNAME:DAE:SP"
        self._surnamepv = prefix + "ED:SURNAME"
        self._orgspv = prefix + "ED:ORGS"

        # Set the channel access server to use
        self.ca = ca

        # Set the data source to use
        self._db = db

        # Create ascii mappings
        ExpData._to_ascii = self._make_ascii_mappings()

    @staticmethod
    def _make_ascii_mappings() -> dict:
        """
        Create mapping for characters not converted to 7 bit by NFKD.
        """
        mappings_in = [ord(char) for char in u'\xd0\xd7\xd8\xde\xdf\xf0\xf8\xfe']
        mappings_out = u'DXOPBoop'
        d = dict(zip(mappings_in, mappings_out))
        d[ord(u'\xc6')] = u'AE'
        d[ord(u'\xe6')] = u'ae'
        return d

    def encode_for_return(self, data: typing.Any) -> bytes:
        """
        Converts data to JSON, compresses it and converts it to hex.

        Args:
            data: The data to encode

        Returns:
            The encoded data
        """
        return compress_and_hex(json.dumps(data))

    def _get_surname_from_fullname(self, fullname: str) -> str:
        try:
            return fullname.split(" ")[-1]
        except:
            return fullname

    def update_experiment_id(self, experiment_id: str) -> None:
        """
        Updates the associated PVs when an experiment ID is set.

        Args:
            experiment_id: the id of the experiment to load related data from

        Returns:
            None specifically, but the following information external to the server is set
            # TODO: Update with the correct PVs for this part

        """
        # Update the RB Number for lookup - SIM for testing, DAE for production
        self.ca.caput(self._simrbpv, experiment_id)
        self.ca.caput(self._daerbpv, experiment_id)

        # Check for the experiment ID
        names = []
        surnames = []
        orgs = []

        if not self._db.experiment_exists(experiment_id):
            self.ca.caput(self._simnames, self.encode_for_return(names))
            self.ca.caput(self._surnamepv, self.encode_for_return(surnames))
            self.ca.caput(self._orgspv, self.encode_for_return(orgs))
            raise Exception("error finding the experiment: %s" % experiment_id)

        # Get the user information from the database and update the associated PVs
        if self._db is not None:
            teammembers = self._db.get_team(experiment_id)
            # Generate the lists/similar for conversion to JSON
            for member in teammembers:
                fullname = six.text_type(member[0])
                org = six.text_type(member[1])
                role = six.text_type(member[2])
                if not role == "Contact":
                    surnames.append(self._get_surname_from_fullname(fullname))
                orgs.append(org)
                name = User(fullname, org, role.lower())
                names.append(name.__dict__)
            orgs = list(set(orgs))
            self.ca.caput(self._simnames, self.encode_for_return(names))
            self.ca.caput(self._surnamepv, self.encode_for_return(surnames))
            self.ca.caput(self._orgspv, self.encode_for_return(orgs))
            # The value put to the dae names pv will need changing in time to use compressed and hexed json etc. but
            # this is not available at this time in the ICP
            self.ca.caput(self._daenamespv, ExpData.make_name_list_ascii(surnames))

    def update_username(self, users: str) -> None:
        """
        Updates the associated PVs when the User Names are altered.

        Args:
            users: uncompressed and dehexed json string with the user details

        Returns:
            None specifically, but the following information external to the server is set
            # TODO: Update with the correct PVs for this part
        """
        names = []
        surnames = []
        orgs = []
        users = json.loads(users)
        # Find user details in deserialized json user data
        for team_member in users:
            fullname = team_member['name']
            # If user only wants to change users not the whole table
            if team_member.get("institute") is None:
                surnames.append(self._get_surname_from_fullname(fullname))
            else:
                org = team_member['institute']
                role = team_member['role']
                if not role == "Contact":
                    surnames.append(self._get_surname_from_fullname(fullname))
                orgs.append(org)
                name = User(fullname, org, role.lower())
                names.append(name.__dict__)
            orgs = list(set(orgs))
        self.ca.caput(self._simnames, self.encode_for_return(names))
        # surname PV is set twice with g.change_users() once from genie python and from database server(here) wait=True
        # makes sure that surname is updated in order. Database server to set it first followed by genie python
        self.ca.caput(self._surnamepv, self.encode_for_return(surnames), wait=True)
        self.ca.caput(self._orgspv, self.encode_for_return(orgs))
        # The value put to the dae names pv will need changing in time to use compressed and hexed json etc. but
        # this is not available at this time in the ICP
        if not surnames:
            self.ca.caput(self._daenamespv, " ")
        else:
            self.ca.caput(self._daenamespv, ExpData.make_name_list_ascii(surnames))

    @staticmethod
    def make_name_list_ascii(names: list) -> bytes:
        """
        Takes a unicode list of names and creates a best ascii comma separated list this implementation is a temporary
        fix until we install the PyPi unidecode module.
        
        Args:
            names: list of unicode names

        Returns:
            comma separated ascii string of names with special characters adjusted
        """
        nlist = u','.join(names)
        nfkd_form = unicodedata.normalize('NFKD', nlist)
        nlist_no_sc = u''.join([c for c in nfkd_form if not unicodedata.combining(c)])
        return nlist_no_sc.translate(ExpData._to_ascii).encode('ascii', 'ignore')
