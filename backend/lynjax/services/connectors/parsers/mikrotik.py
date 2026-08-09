"""Parsers for MikroTik RouterOS CLI output.

Ported from NetVault, where these were validated against a real CRS354-48P and
RouterOS 7.19.3. That hardware is no longer reachable, so the captured samples
in the tests are the only remaining evidence of the real formats: treat them as
fixtures of record and extend rather than replace them.

Fixes applied during the port:

* ARP entries were classified ``static`` whenever the ``D`` flag was absent,
  which mislabelled every DHCP (``H``) and incomplete entry. Flags are now read
  individually.
* MAC addresses are normalised through the shared helper instead of being
  passed through raw, so RouterOS and IOS output can be correlated.
* The interface parser discarded the MAC address it had already matched.
"""

from __future__ import annotations

import re
from typing import Any

from lynjax.services.connectors.base import (
    ArpEntry,
    InterfaceInfo,
    RouteEntry,
    normalize_mac,
)

# 0 RS ether1     ether          1500   1500       4074  48:8F:5A:AA:BB:CC
# Only the leading columns are matched here. The number of numeric columns
# after ACTUAL-MTU varies by model, and consuming them greedily eats the first
# octet of the MAC without backtracking, so the MAC is found separately.
_INTERFACE_RE = re.compile(r"^\s*\d+\s+([A-Za-z]*)\s+(\S+)\s+(\S+)\s+(\d+)")

_MAC_IN_LINE_RE = re.compile(r"\b([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\b")

# 0 D 192.168.88.254  48:8F:5A:AA:BB:CC bridge
_ARP_RE = re.compile(
    r"^\s*\d+\s+([A-Za-z]*)\s+(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9A-Fa-f:]{17})\s+(\S+)"
)

# 0  As  0.0.0.0/0          192.168.88.1           1
_ROUTE_RE = re.compile(r"^\s*\d+\s+([A-Za-z]+)\s+([\d./]+)\s+(\S+)\s+(\d+)")


def parse_system_resource(output: str) -> dict[str, Any]:
    """Parse ``/system resource print``.

    The command emits ``key: value`` pairs one per line, with leading padding
    that varies by key length.
    """
    data: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()

    return {
        "model": data.get("board-name", "MikroTik"),
        "os_version": data.get("version", "Unknown"),
        "uptime": data.get("uptime", "Unknown"),
        "cpu": data.get("cpu", "Unknown"),
        "memory_total": data.get("total-memory", "Unknown"),
        "memory_free": data.get("free-memory", "Unknown"),
    }


def parse_interfaces(output: str) -> list[InterfaceInfo]:
    """Parse ``/interface print``.

    RouterOS marks a running interface with the ``R`` flag. ``S`` means slave
    and ``X`` disabled; only ``R`` indicates the link is actually up.
    """
    interfaces: list[InterfaceInfo] = []

    for line in output.splitlines():
        match = _INTERFACE_RE.search(line)
        if not match:
            continue

        flags, name, _if_type, _mtu = match.groups()
        mac_match = _MAC_IN_LINE_RE.search(line)

        interfaces.append(
            InterfaceInfo(
                name=name,
                status="up" if "R" in flags.upper() else "down",
                mac=normalize_mac(mac_match.group(1)) if mac_match else None,
                ip=None,  # Requires a separate '/ip address print'
            )
        )

    return interfaces


def parse_arp_table(output: str) -> list[ArpEntry]:
    """Parse ``/ip arp print``.

    RouterOS flags: ``D`` dynamic, ``H`` DHCP, ``C`` complete, ``I`` invalid.
    An entry without ``D`` is a manually configured static entry; NetVault
    called every non-``D`` entry static, which also swallowed DHCP leases.
    """
    entries: list[ArpEntry] = []

    for line in output.splitlines():
        match = _ARP_RE.search(line)
        if not match:
            continue

        flags, ip, mac, interface = match.groups()
        flags = flags.upper()

        entry_type = "dynamic" if "D" in flags or "H" in flags else "static"

        entries.append(
            ArpEntry(
                ip=ip,
                mac=normalize_mac(mac),
                interface=interface,
                type=entry_type,
            )
        )

    return entries


def parse_routes(output: str) -> list[RouteEntry]:
    """Parse ``/ip route print``.

    RouterOS flags: ``A`` active, ``C`` connected, ``D`` dynamic, ``S`` static.
    ``C`` is checked before ``D`` because a connected route is also dynamic and
    the more specific label is the useful one.
    """
    routes: list[RouteEntry] = []

    for line in output.splitlines():
        match = _ROUTE_RE.search(line)
        if not match:
            continue

        flags, destination, gateway, distance = match.groups()
        flags = flags.upper()

        if "C" in flags:
            protocol = "connected"
        elif "D" in flags:
            protocol = "dynamic"
        else:
            protocol = "static"

        routes.append(
            RouteEntry(
                destination=destination,
                gateway=gateway,
                # On a connected route the gateway column holds the interface.
                interface=gateway if protocol == "connected" else "",
                metric=int(distance),
                protocol=protocol,
            )
        )

    return routes
