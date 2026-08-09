"""OID catalogue for the SNMP connector.

Every entry is a numeric OID so no MIB files need to be shipped or compiled.
Scalar OIDs end in ``.0``; table column OIDs do not, and are walked.
"""

from __future__ import annotations

# ─── SNMPv2-MIB: the system group ───
SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
SYS_CONTACT = "1.3.6.1.2.1.1.4.0"
SYS_NAME = "1.3.6.1.2.1.1.5.0"
SYS_LOCATION = "1.3.6.1.2.1.1.6.0"

# ─── IF-MIB: ifTable ───
IF_INDEX = "1.3.6.1.2.1.2.2.1.1"
IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
IF_TYPE = "1.3.6.1.2.1.2.2.1.3"
IF_SPEED = "1.3.6.1.2.1.2.2.1.5"
IF_PHYS_ADDRESS = "1.3.6.1.2.1.2.2.1.6"
IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"
IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"
IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"
IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"
IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"

# ─── IF-MIB: ifXTable ───
# ifSpeed is a 32-bit gauge in bits per second, so it saturates at ~4.29 Gbps
# and reports that same ceiling for a 10G port. ifHighSpeed is in Mbps and is
# the only usable figure on modern hardware.
IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
IF_HIGH_SPEED = "1.3.6.1.2.1.31.1.1.1.15"
IF_ALIAS = "1.3.6.1.2.1.31.1.1.1.18"

# ─── IP-MIB: ipNetToMediaTable, the ARP cache ───
IP_NET_TO_MEDIA_IF_INDEX = "1.3.6.1.2.1.4.22.1.1"
IP_NET_TO_MEDIA_PHYS_ADDRESS = "1.3.6.1.2.1.4.22.1.2"
IP_NET_TO_MEDIA_NET_ADDRESS = "1.3.6.1.2.1.4.22.1.3"
IP_NET_TO_MEDIA_TYPE = "1.3.6.1.2.1.4.22.1.4"

# ─── IP-MIB: ipRouteTable ───
IP_ROUTE_DEST = "1.3.6.1.2.1.4.21.1.1"
IP_ROUTE_IF_INDEX = "1.3.6.1.2.1.4.21.1.2"
IP_ROUTE_METRIC1 = "1.3.6.1.2.1.4.21.1.3"
IP_ROUTE_NEXT_HOP = "1.3.6.1.2.1.4.21.1.7"
IP_ROUTE_PROTO = "1.3.6.1.2.1.4.21.1.9"

# ─── BRIDGE-MIB: dot1dTpFdbTable, the MAC forwarding database ───
DOT1D_TP_FDB_ADDRESS = "1.3.6.1.2.1.17.4.3.1.1"
DOT1D_TP_FDB_PORT = "1.3.6.1.2.1.17.4.3.1.2"
DOT1D_TP_FDB_STATUS = "1.3.6.1.2.1.17.4.3.1.3"

# ─── Vendor: MikroTik, enterprise 14988 ───
MIKROTIK_MODEL = "1.3.6.1.4.1.14988.1.1.4.1.0"
MIKROTIK_SERIAL_NUMBER = "1.3.6.1.4.1.14988.1.1.7.3.0"
MIKROTIK_ROUTEROS_VERSION = "1.3.6.1.4.1.14988.1.1.4.4.0"

# ─── Vendor: Cisco, enterprise 9 ───
CISCO_IMAGE_STRING = "1.3.6.1.4.1.9.9.25.1.1.1.2.1.2"
CISCO_MODEL = "1.3.6.1.4.1.9.9.25.1.1.1.2.1.3"

#: ifOperStatus values, from IF-MIB.
IF_OPER_STATUS_NAMES: dict[int, str] = {
    1: "up",
    2: "down",
    3: "testing",
    4: "unknown",
    5: "dormant",
    6: "notPresent",
    7: "lowerLayerDown",
}

#: ipNetToMediaType values, from IP-MIB. NetVault hardcoded every ARP entry as
#: dynamic and never read this column.
ARP_TYPE_NAMES: dict[int, str] = {
    1: "other",
    2: "invalid",
    3: "dynamic",
    4: "static",
}

#: ipRouteProto values, from IP-MIB.
ROUTE_PROTO_NAMES: dict[int, str] = {
    1: "other",
    2: "local",
    3: "netmgmt",
    4: "icmp",
    5: "egp",
    6: "ggp",
    7: "hello",
    8: "rip",
    9: "is-is",
    10: "es-is",
    11: "ciscoIgrp",
    12: "bbnSpfIgp",
    13: "ospf",
    14: "bgp",
}
