from pysnmp.hlapi import *
from pysnmp.smi import builder, compiler, rfc1902, view

from server_common.utilities import SEVERITY, print_and_log

# Assemble MIB browser
mibBuilder = builder.MibBuilder()
mibViewController = view.MibViewController(mibBuilder)

# compiler.addMibCompiler(mibBuilder, sources=['https://mibs.pysnmp.com/asn1/@mib@'], destination='snmp/mibs')
# The below code needs MIBS to have been downloaded in the below subfolder.
compiler.addMibCompiler(mibBuilder, sources=["file://snmp/mibs"])
# Pre-load MIB modules we expect to work with
mibBuilder.loadModules(
    "SNMPv2-MIB", "SNMP-COMMUNITY-MIB", "DISMAN-EXPRESSION-MIB", "RFC1213-MIB", "IF-MIB"
)

INTERESTING_MIBS = [
    "DISMAN-EXPRESSION-MIB::sysUpTimeInstance",
    "SNMPv2-MIB::sysName",
    "IF-MIB::ifOperStatus",
    "IF-MIB::ifSpeed",
    "IF-MIB::ifInOctets",
    "IF-MIB::ifOutOctets",
]


def walk(host, oid, requestedMIBs=INTERESTING_MIBS):
    mibmap = dict()
    for errorIndication, errorStatus, errorIndex, varBinds in nextCmd(
        SnmpEngine(),
        CommunityData("public", mpModel=0),
        UdpTransportTarget((host, 161), timeout=3, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
        lookupMib=False,
        lexicographicMode=False,
        lookupNames=True,
        lookupValues=True,
    ):
        if errorIndication:
            ## we need to look at later - currently will print forever for a moxa that is
            ## not on the network. Maybe return status and let caller decide whether to print
            # print_and_log(f"Error:: for {host}: {errorIndication}", severity=SEVERITY.MINOR)
            break

        elif errorStatus:
            print_and_log(
                "host %s: %s at %s"
                % (
                    host,
                    errorStatus.prettyPrint(),
                    errorIndex and varBinds[int(errorIndex) - 1][0] or "?",
                ),
                severity=SEVERITY.MAJOR,
            )
            break

        else:
            # Run var-binds through MIB resolver
            # You may want to catch and ignore resolution errors here
            varBinds = [
                rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(
                    mibViewController
                )
                for x in varBinds
            ]
            for name, value in varBinds:
                mib, exists, port = name.prettyPrint().partition(".")
                if not exists:
                    port = ""
                # print(name.prettyPrint(), ' = ', value.prettyPrint())
                if mib in requestedMIBs:
                    mibmap[name.prettyPrint()] = value.prettyPrint()
                    # print('MIB-->', mib, ' port-->', port, ' = ', value.prettyPrint())
                    # print_and_log('MIB -->%s, port --> %s, = %s' % (mib, port, value))

    return mibmap


# walk('130.246.49.46', '1.3.6.1.2.1')
