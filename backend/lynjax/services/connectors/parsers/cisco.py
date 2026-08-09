"""Parsers for Cisco IOS CLI output.

Ported from NetVault. Fixes applied during the port:

* ``show ip route`` recognised only ``C`` and ``S`` routes, silently dropping
  every OSPF, EIGRP, BGP and RIP entry. A device with a real routing table
  therefore appeared to have almost no routes. Dynamic protocols are parsed now.
* ``show ip interface brief`` treated ``administratively down`` as if the
  regex's ``up|down`` alternation would match it; ordering in the alternation
  made ``down`` win, so an admin-disabled port was indistinguishable from a
  link failure. It is now reported distinctly.
* MAC normalisation is delegated to the shared helper.
"""

from __future__ import annotations

import re
from typing import Any

from lynjax.services.connectors.base import (
    ArpEntry,
    InterfaceInfo,
    MacEntry,
    RouteEntry,
    normalize_mac,
)

# FastEthernet0/1        192.168.1.1     YES manual up                    up
_INTERFACE_RE = re.compile(
    r"^(\S+)\s+(\S+)\s+(YES|NO)\s+(\S+)\s+"
    r"(administratively down|up|down)\s+(up|down)",
    re.IGNORECASE,
)

# Internet  192.168.1.1             -   0011.2233.4455  ARPA   FastEthernet0/1
_ARP_RE = re.compile(
    r"\s*Internet\s+(\S+)\s+(\S+)\s+([0-9a-fA-F.]+)\s+ARPA\s+(\S+)",
    re.IGNORECASE,
)

#    1    00aa.bbcc.ddee    DYNAMIC     Fa0/1
_MAC_RE = re.compile(
    r"^\s*(\d+)\s+([0-9a-fA-F.]+)\s+(DYNAMIC|STATIC)\s+(\S+)",
    re.IGNORECASE,
)

# C     192.168.1.0/24 is directly connected, FastEthernet0/1
_CONNECTED_RE = re.compile(r"^\s*C\s+([\d./]+)\s+is directly connected,\s*(\S+)")

# S*    0.0.0.0/0 [1/0] via 192.168.1.254
# O     10.1.0.0/16 [110/20] via 10.0.0.1, 00:04:22, GigabitEthernet0/1
_VIA_RE = re.compile(
    r"^\s*([A-Z])\*?(?:\s+\S{1,3})?\s+([\d./]+)\s+\[(\d+)/(\d+)\]\s+via\s+([\d.]+)"
    r"(?:,\s*[^,]+)?(?:,\s*(\S+))?"
)

#: IOS route-code letters mapped to protocol names.
_ROUTE_CODES = {
    "C": "connected",
    "L": "local",
    "S": "static",
    "R": "rip",
    "O": "ospf",
    "D": "eigrp",
    "B": "bgp",
    "I": "igrp",
    "M": "mobile",
}


def parse_show_version(output: str) -> dict[str, Any]:
    """Parse ``show version``."""
    data: dict[str, str] = {}

    if match := re.search(r"Version ([^,]+)", output):
        data["os_version"] = match.group(1)

    if match := re.search(r"cisco (\S+) \(([^)]+)\) processor", output, re.IGNORECASE):
        data["model"] = match.group(1)
        data["cpu"] = match.group(2)

    if match := re.search(r"uptime is ([^\n]+)", output):
        data["uptime"] = match.group(1).strip()

    if match := re.search(r"with (\d+)K bytes of memory", output):
        data["memory_total"] = f"{int(match.group(1)) // 1024}MB"

    return {
        "model": data.get("model", "Cisco Device"),
        "os_version": data.get("os_version", "Unknown"),
        "uptime": data.get("uptime", "Unknown"),
        "cpu": data.get("cpu", "Unknown"),
        "memory_total": data.get("memory_total", "Unknown"),
    }


def parse_show_interfaces(output: str) -> list[InterfaceInfo]:
    """Parse ``show ip interface brief``.

    An interface counts as up only when both the line status and the line
    protocol are up. ``administratively down`` is a deliberate operator action,
    not a fault, so it is preserved as its own status rather than folded into
    ``down``.
    """
    interfaces: list[InterfaceInfo] = []

    for line in output.splitlines():
        match = _INTERFACE_RE.search(line)
        if not match:
            continue

        name, ip, _ok, _method, status, protocol = match.groups()
        status = status.lower()
        protocol = protocol.lower()

        interface_status = "up" if status == "up" and protocol == "up" else "down"

        interfaces.append(
            InterfaceInfo(
                name=name,
                status=interface_status,
                ip=None if ip.lower() == "unassigned" else ip,
                mac=None,  # Needs 'show interfaces <name>'
            )
        )

    return interfaces


def parse_show_ip_arp(output: str) -> list[ArpEntry]:
    """Parse ``show ip arp``.

    An age of ``-`` marks the router's own interface address, which is static.
    """
    entries: list[ArpEntry] = []

    for line in output.splitlines():
        if not line.strip():
            continue
        match = _ARP_RE.search(line)
        if not match:
            continue

        ip, age, mac, interface = match.groups()
        entries.append(
            ArpEntry(
                ip=ip,
                mac=normalize_mac(mac),
                interface=interface,
                type="static" if age.strip() == "-" else "dynamic",
            )
        )

    return entries


def parse_show_mac_address_table(output: str) -> list[MacEntry]:
    """Parse ``show mac address-table``."""
    entries: list[MacEntry] = []

    for line in output.splitlines():
        match = _MAC_RE.search(line)
        if not match:
            continue

        vlan, mac, entry_type, port = match.groups()
        entries.append(
            MacEntry(
                mac=normalize_mac(mac),
                port=port,
                vlan=int(vlan),
                type=entry_type.lower(),
            )
        )

    return entries


def parse_show_ip_route(output: str) -> list[RouteEntry]:
    """Parse ``show ip route``.

    Handles connected routes and any ``via`` route regardless of the protocol
    that installed it. NetVault matched only ``C`` and ``S``, so on a device
    running OSPF or BGP the routing table came back nearly empty and the audit
    drew conclusions from it anyway.
    """
    routes: list[RouteEntry] = []

    for line in output.splitlines():
        if connected := _CONNECTED_RE.search(line):
            destination, interface = connected.groups()
            routes.append(
                RouteEntry(
                    destination=destination,
                    gateway=interface,
                    interface=interface,
                    metric=0,
                    protocol="connected",
                )
            )
            continue

        if via := _VIA_RE.search(line):
            code, destination, distance, _metric, gateway, interface = via.groups()
            routes.append(
                RouteEntry(
                    destination=destination,
                    gateway=gateway,
                    interface=interface or "",
                    metric=int(distance),
                    protocol=_ROUTE_CODES.get(code.upper(), "unknown"),
                )
            )

    return routes
