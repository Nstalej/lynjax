"""Tests for the SNMP connector.

The table-assembly functions are pure, so they are exercised directly with
sample walk output. The connector itself runs against a fake transport, so the
whole collection path is covered without an SNMP agent.
"""

from __future__ import annotations

import pytest

from lynjax.services.connectors import snmp_oids as oids
from lynjax.services.connectors.base import ConnectorError
from lynjax.services.connectors.snmp import (
    SNMPConnector,
    build_arp_entries,
    build_auth_data,
    build_interfaces,
    build_mac_entries,
    build_routes,
    octets_to_mac,
    oid_suffix,
    oid_tail_to_mac,
)


class FakeOctetString:
    """Mimics a pysnmp OctetString carrying raw bytes."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def asOctets(self) -> bytes:  # noqa: N802 - pysnmp's spelling
        return self._payload

    def __str__(self) -> str:
        return self._payload.hex()


class FakeTransport:
    def __init__(
        self,
        scalars: dict[str, object] | None = None,
        walks: dict[str, list[tuple[str, object]]] | None = None,
    ) -> None:
        self.scalars = scalars or {}
        self.walks = walks or {}
        self.requested: list[str] = []
        self.closed = False

    async def get(self, oid: str):
        self.requested.append(oid)
        return self.scalars.get(oid)

    async def walk(self, base_oid: str):
        self.requested.append(base_oid)
        return self.walks.get(base_oid, [])

    async def close(self) -> None:
        self.closed = True


def make_connector(
    scalars=None, walks=None, credentials=None
) -> tuple[SNMPConnector, FakeTransport]:
    transport = FakeTransport(scalars=scalars, walks=walks)
    connector = SNMPConnector(
        "1",
        "10.0.0.1",
        {"version": "v2c", "community": "s3cret", **(credentials or {})},
        transport=transport,
    )
    return connector, transport


class TestOidHelpers:
    def test_suffix_strips_the_base(self):
        assert oid_suffix(f"{oids.IF_DESCR}.3", oids.IF_DESCR) == "3"

    def test_suffix_leaves_an_unrelated_oid_alone(self):
        assert oid_suffix("1.2.3", oids.IF_DESCR) == "1.2.3"

    def test_multi_component_index_is_preserved(self):
        base = oids.IP_NET_TO_MEDIA_PHYS_ADDRESS
        assert oid_suffix(f"{base}.2.10.0.0.5", base) == "2.10.0.0.5"

    def test_octets_become_a_normalised_mac(self):
        value = FakeOctetString(bytes([0x48, 0x8F, 0x5A, 0xAA, 0xBB, 0xCC]))

        assert octets_to_mac(value) == "48:8F:5A:AA:BB:CC"

    def test_oid_tail_becomes_a_mac(self):
        oid = f"{oids.DOT1D_TP_FDB_PORT}.0.170.187.204.221.238"

        assert oid_tail_to_mac(oid) == "00:AA:BB:CC:DD:EE"

    def test_snmp_and_ssh_macs_agree(self):
        """The same NIC seen over both protocols must correlate."""
        from lynjax.services.connectors.parsers.cisco import parse_show_ip_arp

        over_ssh = parse_show_ip_arp(
            "Internet  10.0.0.1  -  00aa.bbcc.ddee  ARPA  Fa0/1"
        )[0].mac
        over_snmp = octets_to_mac(
            FakeOctetString(bytes([0x00, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE]))
        )

        assert over_ssh == over_snmp


class TestBuildInterfaces:
    def test_columns_are_joined_by_index(self):
        """NetVault's version raised AttributeError before reaching this point."""
        interfaces = build_interfaces(
            {
                "descr": [(f"{oids.IF_DESCR}.1", "ether1")],
                "oper_status": [(f"{oids.IF_OPER_STATUS}.1", 1)],
                "in_octets": [(f"{oids.IF_IN_OCTETS}.1", 5000)],
            }
        )

        assert len(interfaces) == 1
        assert interfaces[0].name == "ether1"
        assert interfaces[0].status == "up"
        assert interfaces[0].rx_bytes == 5000

    def test_interfaces_come_back_in_index_order(self):
        interfaces = build_interfaces(
            {
                "descr": [
                    (f"{oids.IF_DESCR}.10", "ether10"),
                    (f"{oids.IF_DESCR}.2", "ether2"),
                    (f"{oids.IF_DESCR}.1", "ether1"),
                ]
            }
        )

        assert [item.name for item in interfaces] == ["ether1", "ether2", "ether10"]

    @pytest.mark.parametrize(
        ("code", "expected"),
        [(1, "up"), (2, "down"), (3, "unknown"), (4, "unknown"), (7, "down")],
    )
    def test_oper_status_codes_map_to_states(self, code, expected):
        interfaces = build_interfaces(
            {"oper_status": [(f"{oids.IF_OPER_STATUS}.1", code)]}
        )

        assert interfaces[0].status == expected

    def test_high_speed_wins_over_the_saturating_32_bit_gauge(self):
        """ifSpeed tops out near 4.29 Gbps and lies about a 10G port."""
        interfaces = build_interfaces(
            {
                "speed": [(f"{oids.IF_SPEED}.1", 4_294_967_295)],
                "high_speed": [(f"{oids.IF_HIGH_SPEED}.1", 10_000)],
            }
        )

        assert interfaces[0].speed == 10_000_000_000

    def test_if_speed_is_used_when_ifxtable_is_absent(self):
        interfaces = build_interfaces(
            {"speed": [(f"{oids.IF_SPEED}.1", 1_000_000_000)]}
        )

        assert interfaces[0].speed == 1_000_000_000

    def test_ifname_is_preferred_over_ifdescr(self):
        interfaces = build_interfaces(
            {
                "descr": [(f"{oids.IF_DESCR}.1", "GigabitEthernet0/1")],
                "name": [(f"{oids.IF_NAME}.1", "Gi0/1")],
            }
        )

        assert interfaces[0].name == "Gi0/1"

    def test_an_index_with_no_name_gets_a_placeholder(self):
        interfaces = build_interfaces(
            {"oper_status": [(f"{oids.IF_OPER_STATUS}.7", 1)]}
        )

        assert interfaces[0].name == "if-7"

    def test_mac_is_normalised(self):
        interfaces = build_interfaces(
            {
                "mac": [
                    (
                        f"{oids.IF_PHYS_ADDRESS}.1",
                        FakeOctetString(bytes([0x48, 0x8F, 0x5A, 0x01, 0x02, 0x03])),
                    )
                ]
            }
        )

        assert interfaces[0].mac == "48:8F:5A:01:02:03"

    def test_no_columns_yields_no_interfaces(self):
        assert build_interfaces({}) == []

    def test_unknown_column_names_are_ignored(self):
        assert build_interfaces({"nonsense": [("1.2.3", "x")]}) == []


class TestBuildArpEntries:
    def test_ip_and_interface_come_from_the_oid_index(self):
        base = oids.IP_NET_TO_MEDIA_PHYS_ADDRESS
        entries = build_arp_entries(
            [(f"{base}.2.192.168.1.50", FakeOctetString(bytes(range(6))))]
        )

        assert entries[0].ip == "192.168.1.50"
        assert entries[0].interface == "2"

    def test_static_bindings_are_reported_as_static(self):
        """NetVault hardcoded every entry as dynamic and hid these."""
        base = oids.IP_NET_TO_MEDIA_PHYS_ADDRESS
        entries = build_arp_entries(
            [(f"{base}.2.192.168.1.50", FakeOctetString(bytes(range(6))))],
            [(f"{oids.IP_NET_TO_MEDIA_TYPE}.2.192.168.1.50", 4)],
        )

        assert entries[0].type == "static"

    def test_dynamic_bindings_are_reported_as_dynamic(self):
        base = oids.IP_NET_TO_MEDIA_PHYS_ADDRESS
        entries = build_arp_entries(
            [(f"{base}.2.192.168.1.50", FakeOctetString(bytes(range(6))))],
            [(f"{oids.IP_NET_TO_MEDIA_TYPE}.2.192.168.1.50", 3)],
        )

        assert entries[0].type == "dynamic"

    def test_a_malformed_index_is_skipped(self):
        base = oids.IP_NET_TO_MEDIA_PHYS_ADDRESS

        assert build_arp_entries([(f"{base}.2", FakeOctetString(b""))]) == []


class TestBuildMacEntries:
    def test_mac_comes_from_the_oid_tail(self):
        entries = build_mac_entries(
            [(f"{oids.DOT1D_TP_FDB_PORT}.0.170.187.204.221.238", 24)]
        )

        assert entries[0].mac == "00:AA:BB:CC:DD:EE"
        assert entries[0].port == "24"

    def test_vlan_is_zero_because_bridge_mib_does_not_carry_it(self):
        """NetVault reported VLAN 1, which is a claim the MIB cannot support."""
        entries = build_mac_entries(
            [(f"{oids.DOT1D_TP_FDB_PORT}.0.170.187.204.221.238", 1)]
        )

        assert entries[0].vlan == 0

    def test_entries_are_marked_learned(self):
        entries = build_mac_entries(
            [(f"{oids.DOT1D_TP_FDB_PORT}.0.170.187.204.221.238", 1)]
        )

        assert entries[0].type == "learned"


class TestBuildRoutes:
    def test_destination_comes_from_the_index_and_gateway_from_the_value(self):
        routes = build_routes([(f"{oids.IP_ROUTE_NEXT_HOP}.0.0.0.0", "10.0.0.1")])

        assert routes[0].destination == "0.0.0.0"
        assert routes[0].gateway == "10.0.0.1"

    def test_metric_and_protocol_are_read_rather_than_assumed(self):
        """Both columns were in the OID catalogue and both went unused."""
        routes = build_routes(
            [(f"{oids.IP_ROUTE_NEXT_HOP}.10.1.0.0", "10.0.0.2")],
            [(f"{oids.IP_ROUTE_METRIC1}.10.1.0.0", 20)],
            [(f"{oids.IP_ROUTE_PROTO}.10.1.0.0", 13)],
        )

        assert routes[0].metric == 20
        assert routes[0].protocol == "ospf"

    def test_an_unreported_metric_of_minus_one_does_not_go_negative(self):
        routes = build_routes(
            [(f"{oids.IP_ROUTE_NEXT_HOP}.0.0.0.0", "10.0.0.1")],
            [(f"{oids.IP_ROUTE_METRIC1}.0.0.0.0", -1)],
        )

        assert routes[0].metric == 0


class TestAuthData:
    def test_v2c_builds_community_data(self):
        assert build_auth_data({"version": "v2c", "community": "public"}) is not None

    def test_sha256_maps_to_sha256_not_sha224(self):
        """NetVault silently downgraded a SHA-256 request to SHA-224."""
        from pysnmp.hlapi.v3arch.asyncio import usmHMAC192SHA256AuthProtocol

        auth = build_auth_data(
            {
                "version": "v3",
                "username": "operator",
                "auth_key": "authkey12345",
                "priv_key": "privkey12345",
                "auth_proto": "sha256",
            }
        )

        # pysnmp 7 deprecated the authProtocol accessor in favour of this one.
        assert auth.authentication_protocol == usmHMAC192SHA256AuthProtocol

    def test_an_unknown_digest_is_rejected_rather_than_silently_downgraded(self):
        with pytest.raises(ConnectorError, match="auth protocol"):
            build_auth_data(
                {"version": "v3", "username": "u", "auth_proto": "sha3-512"}
            )

    def test_an_unknown_privacy_protocol_is_rejected(self):
        with pytest.raises(ConnectorError, match="privacy protocol"):
            build_auth_data({"version": "v3", "username": "u", "priv_proto": "rot13"})

    def test_an_unsupported_version_is_rejected(self):
        with pytest.raises(ConnectorError, match="Unsupported SNMP version"):
            build_auth_data({"version": "v9"})


class TestConnectorLifecycle:
    async def test_a_responding_agent_counts_as_connected(self):
        connector, _ = make_connector({oids.SYS_DESCR: "RouterOS 7.12"})

        assert await connector.connect() is True
        assert connector.is_connected is True

    async def test_a_silent_agent_reports_an_actionable_reason(self):
        connector, _ = make_connector({})

        result = await connector.test_connection()

        assert result.success is False
        assert "UDP 161" in result.error_message

    async def test_disconnect_closes_the_transport(self):
        connector, transport = make_connector({oids.SYS_DESCR: "x"})
        await connector.connect()

        await connector.disconnect()

        assert transport.closed is True
        assert connector.is_connected is False


class TestSystemInfo:
    async def test_routeros_is_identified_from_sysdescr(self):
        connector, _ = make_connector(
            {
                oids.SYS_DESCR: "RouterOS CRS354",
                oids.MIKROTIK_MODEL: "CRS354-48P",
                oids.MIKROTIK_ROUTEROS_VERSION: "7.19.3",
            }
        )

        info = await connector.get_system_info()

        assert info["vendor"] == "mikrotik"
        assert info["model"] == "CRS354-48P"
        assert info["os_version"] == "7.19.3"

    async def test_cisco_is_identified_from_sysdescr(self):
        connector, _ = make_connector(
            {oids.SYS_DESCR: "Cisco IOS Software C2960", oids.CISCO_MODEL: "WS-C2960"}
        )

        info = await connector.get_system_info()

        assert info["vendor"] == "cisco"
        assert info["model"] == "WS-C2960"

    async def test_an_unrecognised_device_stays_generic(self):
        connector, _ = make_connector({oids.SYS_DESCR: "Some NAS appliance"})

        info = await connector.get_system_info()

        assert info["vendor"] == "generic"

    async def test_missing_scalars_become_empty_strings(self):
        connector, _ = make_connector({})

        info = await connector.get_system_info()

        assert info["name"] == ""
        assert info["location"] == ""


class TestCollection:
    async def test_interfaces_are_collected_end_to_end(self):
        connector, _ = make_connector(
            walks={
                oids.IF_DESCR: [(f"{oids.IF_DESCR}.1", "ether1")],
                oids.IF_OPER_STATUS: [(f"{oids.IF_OPER_STATUS}.1", 1)],
            }
        )

        interfaces = await connector.get_interfaces()

        assert [item.name for item in interfaces] == ["ether1"]

    async def test_arp_is_collected_end_to_end(self):
        base = oids.IP_NET_TO_MEDIA_PHYS_ADDRESS
        connector, _ = make_connector(
            walks={base: [(f"{base}.1.10.0.0.5", FakeOctetString(bytes(range(6))))]}
        )

        entries = await connector.get_arp_table()

        assert entries[0].ip == "10.0.0.5"

    async def test_a_device_with_empty_tables_returns_empty_lists(self):
        connector, _ = make_connector()

        assert await connector.get_interfaces() == []
        assert await connector.get_arp_table() == []
        assert await connector.get_mac_table() == []
        assert await connector.get_routes() == []


class TestAudit:
    async def test_v2c_is_flagged_as_cleartext(self):
        connector, _ = make_connector()

        result = await connector.run_audit()
        version_check = next(c for c in result.checks if c.name == "SNMP version")

        assert version_check.status == "warning"
        assert "cleartext" in version_check.message

    async def test_a_default_community_string_is_a_failure(self):
        connector, _ = make_connector(credentials={"community": "public"})

        result = await connector.run_audit()

        assert result.worst_status == "fail"
        assert any(c.name == "Default community string" for c in result.checks)

    async def test_a_unique_community_does_not_trigger_the_default_check(self):
        connector, _ = make_connector(credentials={"community": "Xq7-unique"})

        result = await connector.run_audit()

        assert not any(c.name == "Default community string" for c in result.checks)

    async def test_v3_without_privacy_is_flagged(self):
        connector, _ = make_connector(
            credentials={"version": "v3", "priv_proto": "none"}
        )

        result = await connector.run_audit()
        version_check = next(c for c in result.checks if c.name == "SNMP version")

        assert version_check.status == "warning"

    async def test_v3_with_privacy_passes(self):
        connector, _ = make_connector(
            credentials={"version": "v3", "priv_proto": "aes256"}
        )

        result = await connector.run_audit()
        version_check = next(c for c in result.checks if c.name == "SNMP version")

        assert version_check.status == "pass"

    async def test_interface_errors_are_surfaced(self):
        connector, _ = make_connector(
            credentials={"version": "v3", "priv_proto": "aes"},
            walks={
                oids.IF_DESCR: [(f"{oids.IF_DESCR}.1", "ether1")],
                oids.IF_OPER_STATUS: [(f"{oids.IF_OPER_STATUS}.1", 1)],
                oids.IF_IN_ERRORS: [(f"{oids.IF_IN_ERRORS}.1", 421)],
            },
        )

        result = await connector.run_audit()
        errors_check = next(c for c in result.checks if c.name == "Interface errors")

        assert errors_check.details["interfaces"] == {"ether1": 421}

    async def test_static_arp_bindings_are_surfaced(self):
        base = oids.IP_NET_TO_MEDIA_PHYS_ADDRESS
        connector, _ = make_connector(
            credentials={"version": "v3", "priv_proto": "aes"},
            walks={
                base: [(f"{base}.1.10.0.0.5", FakeOctetString(bytes(range(6))))],
                oids.IP_NET_TO_MEDIA_TYPE: [
                    (f"{oids.IP_NET_TO_MEDIA_TYPE}.1.10.0.0.5", 4)
                ],
            },
        )

        result = await connector.run_audit()

        assert any(c.name == "Static ARP bindings" for c in result.checks)

    async def test_audit_timestamp_is_timezone_aware(self):
        connector, _ = make_connector()

        assert (await connector.run_audit()).timestamp.tzinfo is not None


class TestRealTransport:
    """Guards the pysnmp API surface, which has broken across major versions."""

    async def test_the_transport_can_be_built_and_queried(self):
        """NetVault's UdpTransportTarget(addr, ...).create() raises TypeError on
        pysnmp 7: the address lands on the `timeout` parameter. Nothing caught
        it because the transport was only ever exercised against real hardware.
        Port 16100 has no agent, so this must return None, not raise."""
        from lynjax.services.connectors.snmp import PySnmpTransport

        transport = PySnmpTransport(
            "127.0.0.1",
            16100,
            build_auth_data({"version": "v2c", "community": "public"}),
            timeout=0.3,
            retries=0,
        )

        assert await transport.get("1.3.6.1.2.1.1.1.0") is None
        await transport.close()

    async def test_a_walk_against_a_silent_host_returns_no_rows(self):
        from lynjax.services.connectors.snmp import PySnmpTransport

        transport = PySnmpTransport(
            "127.0.0.1",
            16100,
            build_auth_data({"version": "v2c", "community": "public"}),
            timeout=0.3,
            retries=0,
        )

        assert await transport.walk("1.3.6.1.2.1.2.2.1.2") == []
        await transport.close()

    async def test_closing_releases_the_dispatcher(self):
        """Otherwise pysnmp leaves a pending timeout task per engine."""
        from lynjax.services.connectors.snmp import PySnmpTransport

        transport = PySnmpTransport(
            "127.0.0.1",
            16100,
            build_auth_data({"version": "v2c", "community": "public"}),
            timeout=0.3,
            retries=0,
        )
        await transport.get("1.3.6.1.2.1.1.1.0")

        await transport.close()

        assert transport._target is None


class TestRegistration:
    def test_the_connector_registers_itself_as_snmp(self):
        from lynjax.services.connectors.base import get_connector

        assert get_connector("snmp") is SNMPConnector
