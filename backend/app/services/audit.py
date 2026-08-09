"""Network-wide audit and endpoint chain tracing.

Two things live here.

**Cross-device checks**, ported from NetVault's ``AuditEngine``: duplicate IPs,
duplicate MACs and hosts seen on the wire that nobody registered. These only
work once data from several devices sits side by side.

**Chain tracing**, which is new and is the point of the product. Given the IP of
a machine someone has complained about, walk the collected data outward — ARP to
learn its MAC, MAC tables to find the switch and port it is plugged into,
interface counters to judge the cabling, routes to find the way to the edge —
and report what is wrong at each link. A technician holding a "this computer is
slow" ticket gets an answer about where, not a list of devices.

Everything here is a pure function over a snapshot, so the whole diagnostic is
tested without touching a network.
"""

from __future__ import annotations

import ipaddress
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from app.services.connectors.base import (
    ArpEntry,
    AuditCheck,
    InterfaceInfo,
    MacEntry,
    RouteEntry,
    normalize_mac,
)
from app.services.devices import Device

logger = logging.getLogger("lynjax.audit")

HopRole = Literal["endpoint", "access", "transit", "edge", "unknown"]

#: Inbound errors above this on a single port are worth reporting. Small
#: non-zero counts are normal on links that have been up for months.
ERROR_THRESHOLD = 100


@dataclass
class DeviceSnapshot:
    """What one device reported during a collection run."""

    device: Device
    system_info: dict = field(default_factory=dict)
    interfaces: list[InterfaceInfo] = field(default_factory=list)
    arp: list[ArpEntry] = field(default_factory=list)
    macs: list[MacEntry] = field(default_factory=list)
    routes: list[RouteEntry] = field(default_factory=list)
    error: str | None = None

    def interface(self, name: str) -> InterfaceInfo | None:
        """Find an interface by name, tolerating vendor short forms.

        Switches report a MAC table port as ``Fa0/1`` while the interface table
        says ``FastEthernet0/1``, so an exact match alone would never line the
        two up and the cabling check would never fire.
        """
        lowered = name.lower()
        for interface in self.interfaces:
            if interface.name.lower() == lowered:
                return interface
        for interface in self.interfaces:
            candidate = interface.name.lower()
            if candidate.endswith(lowered) or lowered.endswith(candidate):
                return interface
            # Fa0/1 vs FastEthernet0/1: compare the numeric tail.
            if "/" in lowered and "/" in candidate:
                if lowered.split("/", 1)[1] == candidate.split("/", 1)[1]:
                    if candidate[:2] == lowered[:2]:
                        return interface
        return None


@dataclass
class NetworkSnapshot:
    """Collected state across every device in one run."""

    devices: list[DeviceSnapshot] = field(default_factory=list)

    def registered_hosts(self) -> set[str]:
        return {snapshot.device.host for snapshot in self.devices}


@dataclass
class ChainHop:
    """One link in the path between an endpoint and the edge."""

    role: HopRole
    name: str
    host: str
    device_id: int | None = None
    port: str | None = None
    evidence: str = ""
    findings: list[AuditCheck] = field(default_factory=list)


@dataclass
class ChainTrace:
    """The result of tracing one endpoint outward."""

    target: str
    resolved_mac: str = ""
    hops: list[ChainHop] = field(default_factory=list)
    findings: list[AuditCheck] = field(default_factory=list)
    summary: str = ""

    @property
    def verdict(self) -> str:
        statuses = {check.status for hop in self.hops for check in hop.findings} | {
            check.status for check in self.findings
        }
        if "fail" in statuses:
            return "fail"
        if "warning" in statuses:
            return "warning"
        return "pass"

    @property
    def all_findings(self) -> list[AuditCheck]:
        return [check for hop in self.hops for check in hop.findings] + self.findings


# ─── Cross-device checks ───


def find_duplicate_ips(snapshot: NetworkSnapshot) -> list[AuditCheck]:
    """Report IPs that answer to more than one MAC.

    Usually two machines configured with the same static address, which presents
    to users as intermittent, unexplainable slowness.
    """
    by_ip: dict[str, set[str]] = defaultdict(set)
    for device in snapshot.devices:
        for entry in device.arp:
            if entry.ip and entry.mac:
                by_ip[entry.ip].add(normalize_mac(entry.mac))

    return [
        AuditCheck(
            name="Duplicate IP address",
            status="fail",
            message=(
                f"{ip} answers to {len(macs)} different MAC addresses. Two hosts "
                f"are almost certainly configured with the same address."
            ),
            details={"ip": ip, "macs": sorted(macs)},
        )
        for ip, macs in sorted(by_ip.items())
        if len(macs) > 1
    ]


def find_duplicate_macs(snapshot: NetworkSnapshot) -> list[AuditCheck]:
    """Report a MAC learned on several ports.

    A MAC in two places at once means a loop, a mirrored port, or a moving
    device.
    """
    by_mac: dict[str, set[str]] = defaultdict(set)
    for device in snapshot.devices:
        for entry in device.macs:
            if entry.mac and entry.port:
                by_mac[normalize_mac(entry.mac)].add(
                    f"{device.device.name}:{entry.port}"
                )

    return [
        AuditCheck(
            name="MAC address on multiple ports",
            status="warning",
            message=(
                f"{mac} is learned on {len(ports)} ports. This points to a "
                f"bridging loop or a device that moved without the table ageing out."
            ),
            details={"mac": mac, "ports": sorted(ports)},
        )
        for mac, ports in sorted(by_mac.items())
        if len(ports) > 1
    ]


def find_unmanaged_hosts(snapshot: NetworkSnapshot) -> list[AuditCheck]:
    """Report hosts seen in ARP that are not in the inventory.

    Not a fault on its own; it is the list of things on the network that nobody
    is watching, which is often what an audit is asked to produce.
    """
    known = snapshot.registered_hosts()
    seen: dict[str, str] = {}

    for device in snapshot.devices:
        for entry in device.arp:
            if entry.ip and entry.ip not in known:
                seen.setdefault(entry.ip, normalize_mac(entry.mac))

    if not seen:
        return []

    return [
        AuditCheck(
            name="Unmanaged hosts",
            status="warning",
            message=(
                f"{len(seen)} host(s) are active on the network but not in the "
                f"inventory."
            ),
            details={
                "hosts": [{"ip": ip, "mac": mac} for ip, mac in sorted(seen.items())]
            },
        )
    ]


def audit_interfaces(snapshot: NetworkSnapshot) -> list[AuditCheck]:
    """Report ports whose counters suggest a physical problem."""
    findings: list[AuditCheck] = []

    for device in snapshot.devices:
        erroring = [
            interface
            for interface in device.interfaces
            if interface.errors > ERROR_THRESHOLD
        ]
        if erroring:
            findings.append(
                AuditCheck(
                    name="Interface errors",
                    status="warning",
                    message=(
                        f"{device.device.name} has {len(erroring)} port(s) with "
                        f"significant inbound errors, which usually means bad "
                        f"cabling, a duplex mismatch or a failing transceiver."
                    ),
                    details={
                        "device": device.device.name,
                        "ports": {
                            interface.name: interface.errors for interface in erroring
                        },
                    },
                )
            )

    return findings


def run_network_audit(snapshot: NetworkSnapshot) -> list[AuditCheck]:
    """Every cross-device check, most severe first."""
    findings = (
        find_duplicate_ips(snapshot)
        + find_duplicate_macs(snapshot)
        + audit_interfaces(snapshot)
        + find_unmanaged_hosts(snapshot)
    )
    order = {"fail": 0, "warning": 1, "pass": 2}
    return sorted(findings, key=lambda check: order.get(check.status, 3))


# ─── Chain tracing ───


def resolve_mac(snapshot: NetworkSnapshot, target_ip: str) -> tuple[str, str]:
    """Find the MAC for an IP, and the device that knows it.

    Returns ``(mac, device_name)``; both empty when nothing has an entry.
    """
    for device in snapshot.devices:
        for entry in device.arp:
            if entry.ip == target_ip and entry.mac:
                return normalize_mac(entry.mac), device.device.name
    return "", ""


def locate_mac(
    snapshot: NetworkSnapshot, mac: str
) -> list[tuple[DeviceSnapshot, MacEntry]]:
    """Every switch and port where a MAC has been learned."""
    normalised = normalize_mac(mac)
    return [
        (device, entry)
        for device in snapshot.devices
        for entry in device.macs
        if normalize_mac(entry.mac) == normalised
    ]


def default_route(device: DeviceSnapshot) -> RouteEntry | None:
    for route in device.routes:
        if route.destination in {"0.0.0.0/0", "0.0.0.0", "default"}:
            return route
    return None


def _port_findings(
    device: DeviceSnapshot, port: str, interface: InterfaceInfo | None
) -> list[AuditCheck]:
    """Judge the access port an endpoint is plugged into."""
    if interface is None:
        return [
            AuditCheck(
                name="Access port",
                status="warning",
                message=(
                    f"The endpoint is learned on {device.device.name} port {port}, "
                    f"but that port is not in the interface table, so its health "
                    f"could not be checked."
                ),
            )
        ]

    findings: list[AuditCheck] = []

    if interface.status != "up":
        findings.append(
            AuditCheck(
                name="Access port down",
                status="fail",
                message=(
                    f"{device.device.name} port {interface.name} reports "
                    f"{interface.status}. The endpoint has no working link here."
                ),
                details={"device": device.device.name, "port": interface.name},
            )
        )

    if interface.errors > ERROR_THRESHOLD:
        findings.append(
            AuditCheck(
                name="Access port errors",
                status="fail",
                message=(
                    f"{device.device.name} port {interface.name} has "
                    f"{interface.errors} inbound errors. Bad cabling, a duplex "
                    f"mismatch or a failing transceiver would all produce the "
                    f"slowness being reported."
                ),
                details={"port": interface.name, "errors": interface.errors},
            )
        )

    if interface.speed and interface.speed <= 100_000_000:
        findings.append(
            AuditCheck(
                name="Access port speed",
                status="warning",
                message=(
                    f"{device.device.name} port {interface.name} is linked at "
                    f"{interface.speed // 1_000_000} Mbps. A gigabit endpoint "
                    f"negotiating down to this is a common cause of reported "
                    f"slowness, and usually a cable fault."
                ),
                details={"port": interface.name, "speed_bps": interface.speed},
            )
        )

    if not findings:
        findings.append(
            AuditCheck(
                name="Access port",
                status="pass",
                message=(
                    f"{device.device.name} port {interface.name} is up with no "
                    f"significant errors."
                ),
            )
        )

    return findings


def trace_chain(snapshot: NetworkSnapshot, target_ip: str) -> ChainTrace:
    """Trace one endpoint from its access port out to the edge.

    Answers the question a technician actually has: given this complaint, which
    link in the path is misbehaving?
    """
    trace = ChainTrace(target=target_ip)

    mac, seen_by = resolve_mac(snapshot, target_ip)
    if not mac:
        trace.findings.append(
            AuditCheck(
                name="Endpoint not found",
                status="warning",
                message=(
                    f"No device in the inventory has an ARP entry for {target_ip}. "
                    f"The endpoint may be powered off, on a segment nothing polled "
                    f"reaches, or behind a router whose ARP table was not collected."
                ),
            )
        )
        trace.summary = f"{target_ip} could not be located from the collected data."
        return trace

    trace.resolved_mac = mac
    trace.hops.append(
        ChainHop(
            role="endpoint",
            name=target_ip,
            host=target_ip,
            evidence=f"ARP entry on {seen_by} maps {target_ip} to {mac}.",
        )
    )

    locations = locate_mac(snapshot, mac)
    if not locations:
        trace.findings.append(
            AuditCheck(
                name="Access port unknown",
                status="warning",
                message=(
                    f"{mac} does not appear in any collected MAC address table, so "
                    f"the switch port it is plugged into could not be identified. "
                    f"Collect from the access switches to complete the chain."
                ),
            )
        )
        trace.summary = (
            f"{target_ip} resolves to {mac}, but its access port is unknown."
        )
        return trace

    if len(locations) > 1:
        trace.findings.append(
            AuditCheck(
                name="Endpoint seen in several places",
                status="warning",
                message=(
                    f"{mac} is learned on {len(locations)} ports. The chain below "
                    f"follows the first; a loop or a stale table would explain this."
                ),
                details={
                    "ports": [
                        f"{device.device.name}:{entry.port}"
                        for device, entry in locations
                    ]
                },
            )
        )

    access_device, access_entry = locations[0]
    interface = access_device.interface(access_entry.port)
    trace.hops.append(
        ChainHop(
            role="access",
            name=access_device.device.name,
            host=access_device.device.host,
            device_id=access_device.device.id,
            port=access_entry.port,
            evidence=(
                f"{mac} is learned on {access_device.device.name} "
                f"port {access_entry.port}."
            ),
            findings=_port_findings(access_device, access_entry.port, interface),
        )
    )

    _walk_to_edge(snapshot, access_device, trace)

    problems = [check for check in trace.all_findings if check.status != "pass"]
    if problems:
        worst = next(
            (check for check in problems if check.status == "fail"), problems[0]
        )
        trace.summary = (
            f"{len(trace.hops)} hop(s) traced for {target_ip}. Most likely cause: "
            f"{worst.message}"
        )
    else:
        trace.summary = (
            f"{len(trace.hops)} hop(s) traced for {target_ip}. No fault found along "
            f"the path; look at the endpoint itself or its applications."
        )

    return trace


def _walk_to_edge(
    snapshot: NetworkSnapshot, start: DeviceSnapshot, trace: ChainTrace
) -> None:
    """Follow default routes outward, recording each device we can identify."""
    by_host = {device.device.host: device for device in snapshot.devices}
    current = start
    visited = {current.device.host}

    for _ in range(len(snapshot.devices)):
        route = default_route(current)
        if route is None or not route.gateway:
            break

        gateway = route.gateway
        try:
            ipaddress.ip_address(gateway)
        except ValueError:
            # A connected default route names an interface, not an address.
            break

        if gateway in visited:
            trace.findings.append(
                AuditCheck(
                    name="Routing loop",
                    status="fail",
                    message=(
                        f"Following default routes returned to {gateway}, so the "
                        f"path out is looping."
                    ),
                )
            )
            break

        visited.add(gateway)
        next_device = by_host.get(gateway)

        if next_device is None:
            trace.hops.append(
                ChainHop(
                    role="edge",
                    name=gateway,
                    host=gateway,
                    evidence=(
                        f"{current.device.name} sends unmatched traffic to "
                        f"{gateway}, which is not in the inventory."
                    ),
                    findings=[
                        AuditCheck(
                            name="Edge device not managed",
                            status="warning",
                            message=(
                                f"The path leaves through {gateway}, which is not "
                                f"registered, so nothing beyond this point was "
                                f"checked. Add it to complete the chain."
                            ),
                        )
                    ],
                )
            )
            break

        uplink = next(
            (
                interface
                for interface in current.interfaces
                if interface.status != "up" and interface.ip == gateway
            ),
            None,
        )
        findings: list[AuditCheck] = []
        if uplink is not None:
            findings.append(
                AuditCheck(
                    name="Uplink down",
                    status="fail",
                    message=(
                        f"The uplink from {current.device.name} toward {gateway} "
                        f"is {uplink.status}."
                    ),
                )
            )

        trace.hops.append(
            ChainHop(
                role="transit",
                name=next_device.device.name,
                host=next_device.device.host,
                device_id=next_device.device.id,
                evidence=(
                    f"{current.device.name} routes unmatched traffic to " f"{gateway}."
                ),
                findings=findings,
            )
        )

        current = next_device
