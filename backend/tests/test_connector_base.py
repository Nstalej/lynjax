"""Tests for the connector contract and its shared helpers."""

from __future__ import annotations

from datetime import timezone

import pytest

from app.services.connectors import base
from app.services.connectors.base import (
    AuditCheck,
    AuditResult,
    BaseConnector,
    ConnectionTestResult,
    InterfaceInfo,
    available_connectors,
    get_connector,
    normalize_mac,
    register_connector,
    utc_now,
)


class TestNormalizeMac:
    @pytest.mark.parametrize(
        "raw",
        [
            "00aa.bbcc.ddee",  # Cisco
            "00:aa:bb:cc:dd:ee",  # RouterOS, Linux
            "00-AA-BB-CC-DD-EE",  # Windows
            "00AA.BBCC.DDEE",
            "00aabbccddee",
        ],
    )
    def test_every_vendor_spelling_maps_to_one_form(self, raw):
        """The same NIC must not appear as several devices in one audit."""
        assert normalize_mac(raw) == "00:AA:BB:CC:DD:EE"

    def test_empty_input_returns_empty(self):
        assert normalize_mac("") == ""

    def test_unparseable_input_is_returned_untouched(self):
        """Surface odd values in the report rather than silently mangling them."""
        assert normalize_mac("incomplete") == "incomplete"

    def test_wrong_length_is_not_padded_or_truncated(self):
        assert normalize_mac("00:aa:bb:cc:dd") == "00:aa:bb:cc:dd"

    def test_surrounding_whitespace_is_stripped(self):
        assert normalize_mac("  00aa.bbcc.ddee  ") == "00:AA:BB:CC:DD:EE"


class TestTimestamps:
    def test_utc_now_is_timezone_aware(self):
        """NetVault used naive datetime.utcnow, which broke every comparison."""
        assert utc_now().tzinfo is not None

    def test_utc_now_is_utc(self):
        assert utc_now().utcoffset() == timezone.utc.utcoffset(None)

    def test_audit_result_timestamp_defaults_to_aware_utc(self):
        assert AuditResult(device_name="dev").timestamp.tzinfo is not None


class TestAuditResult:
    def test_worst_status_is_pass_when_no_checks_ran(self):
        assert AuditResult(device_name="dev").worst_status == "pass"

    def test_worst_status_reports_the_most_severe_check(self):
        result = AuditResult(
            device_name="dev",
            checks=[
                AuditCheck(name="a", status="pass", message=""),
                AuditCheck(name="b", status="warning", message=""),
                AuditCheck(name="c", status="fail", message=""),
            ],
        )

        assert result.worst_status == "fail"

    def test_warning_outranks_pass(self):
        result = AuditResult(
            device_name="dev",
            checks=[
                AuditCheck(name="a", status="pass", message=""),
                AuditCheck(name="b", status="warning", message=""),
            ],
        )

        assert result.worst_status == "warning"


class TestImmutability:
    def test_parser_output_cannot_be_rewritten_in_place(self):
        interface = InterfaceInfo(name="ether1", status="up")

        with pytest.raises(Exception):
            interface.name = "tampered"


class _StubConnector(BaseConnector):
    async def connect(self) -> bool:
        self._is_connected = True
        return True

    async def disconnect(self) -> None:
        self._is_connected = False

    async def test_connection(self) -> ConnectionTestResult:
        return ConnectionTestResult(success=True, latency_ms=1.0)

    async def get_system_info(self) -> dict:
        return {}

    async def get_interfaces(self) -> list[InterfaceInfo]:
        return []

    async def run_audit(self) -> AuditResult:
        return AuditResult(device_name="stub")


class TestRegistry:
    @pytest.fixture(autouse=True)
    def _restore_registry(self):
        original = dict(base._REGISTRY)
        yield
        base._REGISTRY.clear()
        base._REGISTRY.update(original)

    def test_a_registered_connector_can_be_looked_up(self):
        register_connector("stub", _StubConnector)

        assert get_connector("stub") is _StubConnector

    def test_lookup_is_case_insensitive(self):
        """Device records are hand-typed; casing must not decide the outcome."""
        register_connector("stub", _StubConnector)

        assert get_connector("STUB") is _StubConnector

    def test_unknown_name_returns_none(self):
        assert get_connector("no-such-connector") is None

    def test_empty_name_returns_none_instead_of_raising(self):
        assert get_connector("") is None

    def test_listing_is_sorted(self):
        register_connector("zulu", _StubConnector)
        register_connector("alpha", _StubConnector)

        names = available_connectors()

        assert names == sorted(names)


class TestConnectorLifecycle:
    async def test_context_manager_connects_and_disconnects(self):
        connector = _StubConnector("1", "10.0.0.1", {})

        async with connector:
            assert connector.is_connected is True

        assert connector.is_connected is False

    async def test_optional_tables_default_to_empty(self):
        """A router has no MAC table; the contract must not force a stub."""
        connector = _StubConnector("1", "10.0.0.1", {})

        assert await connector.get_arp_table() == []
        assert await connector.get_mac_table() == []
        assert await connector.get_routes() == []
