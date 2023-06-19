from collections import OrderedDict
from typing import Dict, Tuple
import winreg as wrg
import socket


GET_MOXA_IPS = """
SELECT moxa_name, moxa_ip
FROM moxa_details.moxa_ips;
"""

GET_MOXA_MAPPINGS_FOR_MOXA_NAME = """
SELECT moxa_port, com_port
FROM moxa_details.port_mappings
WHERE moxa_name = %s;
"""


class MoxaDataSource(object):
    """
    A source for IOC data from the database
    """
    def __init__(self, mysql_abstraction_layer):
        """
        Constructor.

        Args:
            mysql_abstraction_layer(genie_python.mysql_abstraction_layer.AbstractSQLCommands): contact database with sql
        """
        self.mysql_abstraction_layer = mysql_abstraction_layer

    def _query_and_normalise(self, sqlquery, bind_vars=None):
        """
        Executes the given query to the database and converts the data in each row from bytearray to a normal string.
        :param sqlquery: The query to execute.
        :param bind_vars: Any variables to bind to query. Defaults to None.
        :return: A list of lists of strings, representing the data from the table.
        """
        # Get as a plain list of lists
        values = [list(element) for element in self.mysql_abstraction_layer.query(sqlquery, bind_vars)]

        # Convert any bytearrays
        for i, pv in enumerate(values):
            for j, element in enumerate(pv):
                if type(element) == bytearray:
                    values[i][j] = element.decode("utf-8")
        return values

    def insert_mappings(self, moxa_ip_name_dict, moxa_ports_dict):
        pass

class MoxaData():

    def __init__(self, data_source, prefix):
        """Constructor

        Args:
            data_source (IocDataSource): The wrapper for the database that holds IOC information
            procserver (ProcServWrapper): An instance of ProcServWrapper, used to start and stop IOCs
            prefix (string): The pv prefix of the instrument the server is being run on
        """
        self._moxa_data_source = data_source
        self._prefix = prefix
        self.moxa_map = OrderedDict()
        # insert mappings initially
        self._moxa_data_source.insert_mappings(*self._get_mappings())

    def _get_mappings(self) -> Tuple[Dict[str, str], Dict[int, int]]:
        # moxa_name_ip_dict: HOSTNAME:IPADDR
        # moxa_ports_dict: HOSTNAME:{PHYSPORT:COMPORT}
        moxa_name_ip_dict = dict()
        moxa_ports_dict = dict()

        location = wrg.HKEY_LOCAL_MACHINE
        params = wrg.OpenKeyEx(location,r"SYSTEM\\CurrentControlSet\\Services\\npdrv\\Parameters")
        server_count = wrg.QueryValueEx(params, "Servers")[0]

        for server_num in range(1, server_count+1):
            soft = wrg.OpenKeyEx(location,f"SYSTEM\\CurrentControlSet\\Services\\npdrv\\Parameters\\Server{server_num}")
            ip_addr_bytes = wrg.QueryValueEx(soft,"IPAddress")[0].to_bytes(4)
            ip_addr = ".".join([str(int(x)) for x in ip_addr_bytes])
            hostname = socket.gethostbyaddr(ip_addr)[0]
            moxa_name_ip_dict[hostname] = ip_addr
            print(f"IP {ip_addr} hostname {hostname}")
            start_num_com = 1
            com_nums = enumerate(wrg.QueryValueEx(soft,"COMNO")[0], start_num_com)
            moxa_ports_dict[hostname] = com_nums
            for count, value in com_nums: 
                print(f"physical port {count} COM number {value}")

        return moxa_name_ip_dict, moxa_ports_dict

