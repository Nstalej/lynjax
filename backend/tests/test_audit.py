"""Tests for the network audit and the endpoint chain trace."""

from __future__ import annotations

import pytest

from app.services.audit import (
    ChainTrace,
    DeviceSnapshot,
    NetworkSnapshot,
    find_duplicate_ips,
    find_duplicate_macs,
    find_unmanaged_hosts,
    locate_mac,
    resolve_mac,
    run_network_audit,
    trace_chain,
)
from app.services.connectors.base import (
    ArpEntry,
    InterfaceInfo,
    MacEntry,
    RouteEntry,
)
from app.services.devices import Device

ENDPOINT_IP = "10.0.0.50"
ENDPOINT_MAC = "00:AA:BB:CC:DD:EE"


def device(name: str, host: str, device_id: int = 1) -> Device:
    return Device(id=device_id, name=name, host=host, connector_type="ssh")


def access_switch(
    *,
    port_status: str = "up",
    errors: int = 0,
    speed: int | None = 1_000_000_000,
    port_name: str = "Fa0/1",
    interface_name: str = "FastEthernet0/1",
    gateway: str = "10.0.0.254",
) -> DeviceSnapshot:
    return DeviceSnapshot(
        device=device("access-sw", "10.0.0.2", 2),
        interfaces=[
            InterfaceInfo(
                name=interface_name, status=port_status, errors=errors, speed=speed
            )
        ],
        macs=[MacEntry(mac=ENDPOINT_MAC, port=port_name, vlan=1, type="learned")],
        routes=[
            RouteEntry(
                destination="0.0.0.0/0",
                gateway=gateway,
                interface="",
                metric=1,
                protocol="static",
            )
        ],
    )


def gateway_router(host: str = "10.0.0.254") -> DeviceSnapshot:
    return DeviceSnapshot(
        device=device("core-router", host, 3),
        arp=[
            ArpEntry(
                ip=ENDPOINT_IP, mac=ENDPOINT_MAC, interface="vlan1", type="dynamic"
            )
        ],
        routes=[
            RouteEntry(
                destination="0.0.0.0/0",
                gateway="203.0.113.1",
                interface="",
                metric=1,
                protocol="static",
            )
        ],
    )


def full_network(**kwargs) -> NetworkSnapshot:
    return NetworkSnapshot(devices=[gateway_router(), access_switch(**kwargs)])


class TestDuplicateDetection:
    def test_an_ip_answering_to_two_macs_is_a_failure(self):
        snapshot = NetworkSnapshot(
            devices=[
                DeviceSnapshot(
                    device=device("r1", "10.0.0.1"),
                    arp=[
                        ArpEntry(
                            ip="10.0.0.9",
                            mac="AA:AA:AA:AA:AA:AA",
                            interface="",
                            type="dynamic",
                        ),
                        ArpEntry(
                            ip="10.0.0.9",
                            mac="BB:BB:BB:BB:BB:BB",
                            interface="",
                            type="dynamic",
                        ),
                    ],
                )
            ]
        )

        findings = find_duplicate_ips(snapshot)

        assert findings[0].status == "fail"
        assert findings[0].details["ip"] == "10.0.0.9"

    def test_the_same_mac_written_two_ways_is_not_a_duplicate(self):
        """Cisco dotted and colon forms are one host, not two."""
        snapshot = NetworkSnapshot(
            devices=[
                DeviceSnapshot(
                    device=device("r1", "10.0.0.1"),
                    arp=[
                        ArpEntry(
                            ip="10.0.0.9",
                            mac="00aa.bbcc.ddee",
                            interface="",
                            type="dynamic",
                        ),
                        ArpEntry(
                            ip="10.0.0.9",
                            mac="00:AA:BB:CC:DD:EE",
                            interface="",
                            type="dynamic",
                        ),
                    ],
                )
            ]
        )

        assert find_duplicate_ips(snapshot) == []

    def test_a_mac_on_two_ports_is_a_warning(self):
        snapshot = NetworkSnapshot(
            devices=[
                DeviceSnapshot(
                    device=device("sw1", "10.0.0.2"),
                    macs=[
                        MacEntry(
                            mac=ENDPOINT_MAC, port="Fa0/1", vlan=1, type="learned"
                        ),
                        MacEntry(
                            mac=ENDPOINT_MAC, port="Fa0/9", vlan=1, type="learned"
                        ),
                    ],
                )
            ]
        )

        findings = find_duplicate_macs(snapshot)

        assert findings[0].status == "warning"
        assert len(findings[0].details["ports"]) == 2

    def test_a_clean_network_produces_no_findings(self):
        assert find_duplicate_ips(full_network()) == []
        assert find_duplicate_macs(full_network()) == []


class TestUnmanagedHosts:
    def test_hosts_in_arp_but_not_in_the_inventory_are_listed(self):
        findings = find_unmanaged_hosts(full_network())

        assert findings[0].details["hosts"][0]["ip"] == ENDPOINT_IP

    def test_registered_devices_are_not_reported_as_unmanaged(self):
        snapshot = NetworkSnapshot(
            devices=[
                DeviceSnapshot(
                    device=device("r1", "10.0.0.1"),
                    arp=[
                        ArpEntry(
                            ip="10.0.0.1",
                            mac="AA:AA:AA:AA:AA:AA",
                            interface="",
                            type="dynamic",
                        )
                    ],
                )
            ]
        )

        assert find_unmanaged_hosts(snapshot) == []


class TestNetworkAudit:
    def test_findings_are_ordered_most_severe_first(self):
        snapshot = NetworkSnapshot(
            devices=[
                DeviceSnapshot(
                    device=device("r1", "10.0.0.1"),
                    arp=[
                        ArpEntry(
                            ip="10.0.0.9",
                            mac="AA:AA:AA:AA:AA:AA",
                            interface="",
                            type="dynamic",
                        ),
                        ArpEntry(
                            ip="10.0.0.9",
                            mac="BB:BB:BB:BB:BB:BB",
                            interface="",
                            type="dynamic",
                        ),
                    ],
                )
            ]
        )

        statuses = [check.status for check in run_network_audit(snapshot)]

        assert statuses == sorted(statuses, key=lambda s: {"fail": 0, "warning": 1}[s])

    def test_an_empty_snapshot_produces_no_findings(self):
        assert run_network_audit(NetworkSnapshot()) == []


class TestLookups:
    def test_an_ip_resolves_to_its_mac(self):
        mac, seen_by = resolve_mac(full_network(), ENDPOINT_IP)

        assert mac == ENDPOINT_MAC
        assert seen_by == "core-router"

    def test_an_unknown_ip_resolves_to_nothing(self):
        assert resolve_mac(full_network(), "10.0.0.99") == ("", "")

    def test_a_mac_is_located_on_its_switch_port(self):
        locations = locate_mac(full_network(), ENDPOINT_MAC)

        assert locations[0][1].port == "Fa0/1"

    def test_lookup_tolerates_a_different_mac_spelling(self):
        assert locate_mac(full_network(), "00aa.bbcc.ddee")


class TestInterfaceMatching:
    def test_a_short_port_name_matches_the_long_interface_name(self):
        """Switches say Fa0/1 in the MAC table and FastEthernet0/1 in ifTable."""
        snapshot = access_switch()

        assert snapshot.interface("Fa0/1").name == "FastEthernet0/1"

    def test_an_exact_name_matches(self):
        snapshot = access_switch(port_name="ether1", interface_name="ether1")

        assert snapshot.interface("ether1").name == "ether1"

    def test_an_unknown_port_returns_none(self):
        assert access_switch().interface("Gi9/9") is None


class TestChainTrace:
    def test_a_healthy_path_raises_no_failure(self):
        """The default fixture ends at an unmanaged edge, which is a warning:
        we genuinely cannot see past it, and saying "all clear" would overclaim."""
        trace = trace_chain(full_network(), ENDPOINT_IP)

        assert trace.verdict == "warning"
        assert not any(check.status == "fail" for check in trace.all_findings)

    def test_a_fully_managed_chain_reports_no_fault(self):
        snapshot = full_network()
        edge = DeviceSnapshot(
            device=device("edge-fw", "203.0.113.1", 4),
            routes=[],
        )
        snapshot.devices.append(edge)

        trace = trace_chain(snapshot, ENDPOINT_IP)

        assert trace.verdict == "pass"
        assert "No fault found" in trace.summary

    def test_the_chain_starts_at_the_endpoint(self):
        trace = trace_chain(full_network(), ENDPOINT_IP)

        assert trace.hops[0].role == "endpoint"
        assert trace.hops[0].name == ENDPOINT_IP
        assert trace.resolved_mac == ENDPOINT_MAC

    def test_the_access_switch_and_port_are_identified(self):
        """The core question: where is this machine actually plugged in?"""
        trace = trace_chain(full_network(), ENDPOINT_IP)
        access = next(hop for hop in trace.hops if hop.role == "access")

        assert access.name == "access-sw"
        assert access.port == "Fa0/1"

    def test_every_hop_carries_its_evidence(self):
        trace = trace_chain(full_network(), ENDPOINT_IP)

        assert all(hop.evidence for hop in trace.hops)

    def test_the_path_continues_to_the_router(self):
        trace = trace_chain(full_network(), ENDPOINT_IP)

        assert [hop.role for hop in trace.hops] == [
            "endpoint",
            "access",
            "transit",
            "edge",
        ]

    def test_a_missing_endpoint_says_so_instead_of_guessing(self):
        trace = trace_chain(full_network(), "10.0.0.99")

        assert trace.verdict == "warning"
        assert "could not be located" in trace.summary

    def test_an_endpoint_with_no_known_switch_port_says_so(self):
        snapshot = NetworkSnapshot(devices=[gateway_router()])

        trace = trace_chain(snapshot, ENDPOINT_IP)

        assert trace.resolved_mac == ENDPOINT_MAC
        assert "access port is unknown" in trace.summary


class TestChainDiagnosis:
    def test_a_down_access_port_is_the_headline(self):
        trace = trace_chain(full_network(port_status="down"), ENDPOINT_IP)

        assert trace.verdict == "fail"
        assert "no working link" in trace.summary

    def test_a_port_with_errors_names_cabling_as_the_cause(self):
        """The exact ticket: "this computer is slow", answered with a port."""
        trace = trace_chain(full_network(errors=5000), ENDPOINT_IP)

        assert trace.verdict == "fail"
        assert "cabling" in trace.summary

    def test_a_port_negotiated_down_to_100mbps_is_flagged(self):
        trace = trace_chain(full_network(speed=100_000_000), ENDPOINT_IP)

        assert trace.verdict == "warning"
        assert "100 Mbps" in trace.summary

    def test_an_unmanaged_edge_is_reported_rather_than_ignored(self):
        trace = trace_chain(full_network(), ENDPOINT_IP)
        edge = next(hop for hop in trace.hops if hop.role == "edge")

        assert edge.findings[0].status == "warning"
        assert "not registered" in edge.findings[0].message

    def test_an_endpoint_on_two_ports_is_flagged(self):
        snapshot = full_network()
        snapshot.devices[1].macs.append(
            MacEntry(mac=ENDPOINT_MAC, port="Fa0/9", vlan=1, type="learned")
        )

        trace = trace_chain(snapshot, ENDPOINT_IP)

        assert any("several places" in check.name for check in trace.findings)

    def test_a_routing_loop_is_detected(self):
        looping = access_switch(gateway="10.0.0.254")
        router = gateway_router()
        router.routes = [
            RouteEntry(
                destination="0.0.0.0/0",
                gateway="10.0.0.2",
                interface="",
                metric=1,
                protocol="static",
            )
        ]
        second = DeviceSnapshot(
            device=device("access-sw", "10.0.0.2", 2),
            macs=looping.macs,
            interfaces=looping.interfaces,
            routes=[
                RouteEntry(
                    destination="0.0.0.0/0",
                    gateway="10.0.0.254",
                    interface="",
                    metric=1,
                    protocol="static",
                )
            ],
        )
        snapshot = NetworkSnapshot(devices=[router, second])

        trace = trace_chain(snapshot, ENDPOINT_IP)

        assert any(check.name == "Routing loop" for check in trace.findings)


class TestVerdict:
    def test_an_empty_trace_passes(self):
        assert ChainTrace(target="10.0.0.1").verdict == "pass"

    @pytest.mark.parametrize(
        ("statuses", "expected"),
        [
            (["pass"], "pass"),
            (["pass", "warning"], "warning"),
            (["warning", "fail"], "fail"),
        ],
    )
    def test_the_worst_status_wins(self, statuses, expected):
        from app.services.audit import AuditCheck, ChainHop

        trace = ChainTrace(
            target="10.0.0.1",
            hops=[
                ChainHop(
                    role="access",
                    name="sw",
                    host="10.0.0.2",
                    findings=[
                        AuditCheck(name="c", status=status, message="")
                        for status in statuses
                    ],
                )
            ],
        )

        assert trace.verdict == expected
