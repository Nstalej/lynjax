"""Tests for the Cisco IOS parsers.

Samples captured during NetVault field work, plus cases added here for the
formats NetVault's regexes silently dropped.
"""

from __future__ import annotations

from app.services.connectors.parsers import cisco

SHOW_VERSION = """
Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 12.2(55)SE7, RELEASE SOFTWARE (fc1)
cisco WS-C2960-24TT-L (PowerPC405) processor (revision B0) with 65536K bytes of memory.
Switch uptime is 2 weeks, 1 day, 3 hours, 2 minutes
""".strip()

SHOW_IP_INTERFACE_BRIEF = """
Interface              IP-Address      OK? Method Status                Protocol
FastEthernet0/1        192.168.1.1     YES manual up                    up
FastEthernet0/2        unassigned      YES unset  down                  down
FastEthernet0/3        unassigned      YES unset  administratively down down
""".strip()

SHOW_IP_ARP = """
Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  192.168.1.1             -   0011.2233.4455  ARPA   FastEthernet0/1
Internet  192.168.1.100          10   00aa.bbcc.ddee  ARPA   FastEthernet0/1
""".strip()

MAC_TABLE = """
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       ----        -----
   1    00aa.bbcc.ddee    DYNAMIC     Fa0/1
  10    0011.2233.4455    STATIC      Fa0/2
""".strip()

IP_ROUTE = """
S*    0.0.0.0/0 [1/0] via 192.168.1.254
C     192.168.1.0/24 is directly connected, FastEthernet0/1
O     10.1.0.0/16 [110/20] via 10.0.0.1, 00:04:22, GigabitEthernet0/1
D     172.16.0.0/16 [90/2195456] via 10.0.0.2, 00:12:05, GigabitEthernet0/2
B     203.0.113.0/24 [20/0] via 198.51.100.1, 3d02h
""".strip()


class TestShowVersion:
    def test_extracts_model_and_os_version(self):
        parsed = cisco.parse_show_version(SHOW_VERSION)

        assert parsed["model"] == "WS-C2960-24TT-L"
        assert parsed["os_version"] == "12.2(55)SE7"

    def test_extracts_uptime_and_cpu(self):
        parsed = cisco.parse_show_version(SHOW_VERSION)

        assert parsed["uptime"] == "2 weeks, 1 day, 3 hours, 2 minutes"
        assert parsed["cpu"] == "PowerPC405"

    def test_converts_memory_to_megabytes(self):
        parsed = cisco.parse_show_version(SHOW_VERSION)

        assert parsed["memory_total"] == "64MB"

    def test_unrecognised_output_falls_back(self):
        parsed = cisco.parse_show_version("something entirely different")

        assert parsed["model"] == "Cisco Device"
        assert parsed["os_version"] == "Unknown"


class TestInterfaces:
    def test_interface_is_up_only_when_status_and_protocol_agree(self):
        interfaces = cisco.parse_show_interfaces(SHOW_IP_INTERFACE_BRIEF)

        assert interfaces[0].name == "FastEthernet0/1"
        assert interfaces[0].status == "up"
        assert interfaces[0].ip == "192.168.1.1"

    def test_down_interface_is_reported_down(self):
        interfaces = cisco.parse_show_interfaces(SHOW_IP_INTERFACE_BRIEF)

        assert interfaces[1].status == "down"

    def test_administratively_down_interface_is_parsed(self):
        """NetVault's alternation could not match this line at all."""
        interfaces = cisco.parse_show_interfaces(SHOW_IP_INTERFACE_BRIEF)

        assert len(interfaces) == 3
        assert interfaces[2].name == "FastEthernet0/3"
        assert interfaces[2].status == "down"

    def test_unassigned_address_becomes_none(self):
        interfaces = cisco.parse_show_interfaces(SHOW_IP_INTERFACE_BRIEF)

        assert interfaces[1].ip is None

    def test_header_row_is_not_parsed_as_an_interface(self):
        interfaces = cisco.parse_show_interfaces(SHOW_IP_INTERFACE_BRIEF)

        assert "Interface" not in [i.name for i in interfaces]


class TestArp:
    def test_cisco_dotted_mac_is_normalised(self):
        entries = cisco.parse_show_ip_arp(SHOW_IP_ARP)

        assert entries[0].mac == "00:11:22:33:44:55"

    def test_dash_age_marks_the_routers_own_address_as_static(self):
        entries = cisco.parse_show_ip_arp(SHOW_IP_ARP)

        assert entries[0].type == "static"
        assert entries[1].type == "dynamic"

    def test_parses_every_entry(self):
        entries = cisco.parse_show_ip_arp(SHOW_IP_ARP)

        assert [e.ip for e in entries] == ["192.168.1.1", "192.168.1.100"]

    def test_empty_output_yields_no_entries(self):
        assert cisco.parse_show_ip_arp("") == []


class TestMacAddressTable:
    def test_parses_vlan_mac_type_and_port(self):
        entries = cisco.parse_show_mac_address_table(MAC_TABLE)

        assert entries[0].mac == "00:AA:BB:CC:DD:EE"
        assert entries[0].vlan == 1
        assert entries[0].port == "Fa0/1"
        assert entries[0].type == "dynamic"

    def test_static_entries_are_labelled(self):
        entries = cisco.parse_show_mac_address_table(MAC_TABLE)

        assert entries[1].type == "static"
        assert entries[1].vlan == 10

    def test_separator_rows_are_ignored(self):
        entries = cisco.parse_show_mac_address_table(MAC_TABLE)

        assert len(entries) == 2


class TestRoutes:
    def test_static_default_route_is_parsed(self):
        routes = cisco.parse_show_ip_route(IP_ROUTE)
        static = [r for r in routes if r.protocol == "static"]

        assert static[0].destination == "0.0.0.0/0"
        assert static[0].gateway == "192.168.1.254"

    def test_connected_route_records_the_interface(self):
        routes = cisco.parse_show_ip_route(IP_ROUTE)
        connected = [r for r in routes if r.protocol == "connected"]

        assert connected[0].destination == "192.168.1.0/24"
        assert connected[0].interface == "FastEthernet0/1"

    def test_ospf_route_is_parsed(self):
        """NetVault matched only C and S, so OSPF routes vanished."""
        routes = cisco.parse_show_ip_route(IP_ROUTE)
        ospf = [r for r in routes if r.protocol == "ospf"]

        assert ospf[0].destination == "10.1.0.0/16"
        assert ospf[0].gateway == "10.0.0.1"

    def test_eigrp_route_is_parsed(self):
        routes = cisco.parse_show_ip_route(IP_ROUTE)
        eigrp = [r for r in routes if r.protocol == "eigrp"]

        assert eigrp[0].destination == "172.16.0.0/16"

    def test_bgp_route_is_parsed(self):
        routes = cisco.parse_show_ip_route(IP_ROUTE)
        bgp = [r for r in routes if r.protocol == "bgp"]

        assert bgp[0].destination == "203.0.113.0/24"

    def test_every_route_in_the_sample_is_accounted_for(self):
        """A dropped route silently weakens any audit drawn from the table."""
        assert len(cisco.parse_show_ip_route(IP_ROUTE)) == 5

    def test_empty_output_yields_no_routes(self):
        assert cisco.parse_show_ip_route("") == []
