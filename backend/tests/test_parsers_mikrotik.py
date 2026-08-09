"""Tests for the RouterOS parsers.

The samples below were captured from a real CRS354-48P running RouterOS 7.x
during NetVault field work. That hardware is no longer reachable, so these
strings are the only surviving record of the actual output format. Extend them,
do not rewrite them.
"""

from __future__ import annotations

from lynjax.services.connectors.parsers import mikrotik

SYSTEM_RESOURCE = """
             uptime: 5d21h34m56s
            version: 7.12.1 (stable)
         board-name: RB750Gr3
                cpu: MIPS 24Kc V7.4
       total-memory: 128.0MiB
        free-memory: 110.4MiB
""".strip()

INTERFACES = """
Flags: R - RUNNING; S - SLAVE
#    NAME       TYPE     ACTUAL-MTU  L2MTU  MAX-L2MTU  MAC-ADDRESS
0 RS ether1     ether          1500   1500       4074  48:8F:5A:AA:BB:CC
1    ether2     ether          1500   1500       4074  48:8F:5A:AA:BB:CD
""".strip()

ARP = """
#   ADDRESS         MAC-ADDRESS       INTERFACE
0 D 192.168.88.254  48:8F:5A:AA:BB:CC bridge
1   192.168.88.2    4C:5E:0C:11:22:33 ether1
2 DH 192.168.88.50  AA:BB:CC:DD:EE:FF bridge
""".strip()

ROUTES = """
#      DST-ADDRESS        GATEWAY         DISTANCE
0  As  0.0.0.0/0          192.168.88.1           1
1  DAC 192.168.88.0/24    bridge                 0
""".strip()


class TestSystemResource:
    def test_extracts_identity_fields(self):
        parsed = mikrotik.parse_system_resource(SYSTEM_RESOURCE)

        assert parsed["model"] == "RB750Gr3"
        assert parsed["os_version"] == "7.12.1 (stable)"
        assert parsed["uptime"] == "5d21h34m56s"
        assert parsed["memory_total"] == "128.0MiB"
        assert parsed["memory_free"] == "110.4MiB"

    def test_missing_fields_fall_back_rather_than_raising(self):
        parsed = mikrotik.parse_system_resource("uptime: 1d")

        assert parsed["model"] == "MikroTik"
        assert parsed["os_version"] == "Unknown"

    def test_empty_output_is_handled(self):
        assert mikrotik.parse_system_resource("")["model"] == "MikroTik"

    def test_values_containing_colons_are_kept_whole(self):
        """A MAC or time value in the payload must not be split at the colon."""
        parsed = mikrotik.parse_system_resource("cpu: MIPS 24Kc V7.4\nuptime: 1d2h3m")

        assert parsed["cpu"] == "MIPS 24Kc V7.4"


class TestInterfaces:
    def test_running_flag_decides_status(self):
        interfaces = mikrotik.parse_interfaces(INTERFACES)

        assert [i.name for i in interfaces] == ["ether1", "ether2"]
        assert interfaces[0].status == "up"
        assert interfaces[1].status == "down"

    def test_mac_address_is_captured_and_normalised(self):
        """NetVault matched the MAC column and then discarded it."""
        interfaces = mikrotik.parse_interfaces(INTERFACES)

        assert interfaces[0].mac == "48:8F:5A:AA:BB:CC"

    def test_empty_output_yields_no_interfaces(self):
        assert mikrotik.parse_interfaces("") == []

    def test_header_lines_are_ignored(self):
        interfaces = mikrotik.parse_interfaces(
            "Flags: R - RUNNING; S - SLAVE\n" "#    NAME       TYPE     ACTUAL-MTU\n"
        )

        assert interfaces == []


class TestArpTable:
    def test_parses_address_mac_and_interface(self):
        entries = mikrotik.parse_arp_table(ARP)

        assert entries[0].ip == "192.168.88.254"
        assert entries[0].mac == "48:8F:5A:AA:BB:CC"
        assert entries[0].interface == "bridge"

    def test_dynamic_flag_is_honoured(self):
        entries = mikrotik.parse_arp_table(ARP)

        assert entries[0].type == "dynamic"

    def test_entry_without_flags_is_static(self):
        entries = mikrotik.parse_arp_table(ARP)

        assert entries[1].type == "static"

    def test_dhcp_entry_is_dynamic_not_static(self):
        """The DH flag marks a DHCP lease. NetVault labelled these static."""
        entries = mikrotik.parse_arp_table(ARP)

        assert entries[2].ip == "192.168.88.50"
        assert entries[2].type == "dynamic"

    def test_empty_output_yields_no_entries(self):
        assert mikrotik.parse_arp_table("") == []


class TestRoutes:
    def test_static_route_carries_gateway_and_distance(self):
        routes = mikrotik.parse_routes(ROUTES)

        assert routes[0].destination == "0.0.0.0/0"
        assert routes[0].gateway == "192.168.88.1"
        assert routes[0].metric == 1
        assert routes[0].protocol == "static"

    def test_connected_route_is_labelled_connected_not_dynamic(self):
        """DAC carries both D and C; the specific label is the useful one."""
        routes = mikrotik.parse_routes(ROUTES)

        assert routes[1].protocol == "connected"

    def test_connected_route_records_the_interface(self):
        routes = mikrotik.parse_routes(ROUTES)

        assert routes[1].interface == "bridge"

    def test_empty_output_yields_no_routes(self):
        assert mikrotik.parse_routes("") == []
