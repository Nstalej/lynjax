"""Tests for the SSH connector.

NetVault's version had no tests, because it built its paramiko client inline and
could only be exercised against live hardware. The connector now takes a client
factory, so the whole command path is testable with a fake transport and no
network access.
"""

from __future__ import annotations

import paramiko
import pytest

from lynjax.services.connectors.base import (
    ConnectorAuthError,
    ConnectorUnreachableError,
)
from lynjax.services.connectors.ssh import SSHConnector
from tests.test_parsers_cisco import SHOW_IP_INTERFACE_BRIEF, SHOW_VERSION
from tests.test_parsers_mikrotik import ARP, INTERFACES, SYSTEM_RESOURCE

CREDENTIALS = {
    "username": "operator",
    "password": "s3cr3t",
    "port": 22,
    "timeout": 1,
    "device_type": "mikrotik",
}


class FakeStdout:
    def __init__(self, payload: str) -> None:
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload


class FakeSSHClient:
    """Stands in for paramiko.SSHClient, recording what the connector asks for."""

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        connect_error: Exception | None = None,
    ) -> None:
        self.responses = responses or {}
        self.connect_error = connect_error
        self.commands: list[str] = []
        self.connect_kwargs: dict | None = None
        self.closed = False
        self.host_key_policy = None
        self.loaded_system_keys = False

    def load_system_host_keys(self) -> None:
        self.loaded_system_keys = True

    def load_host_keys(self, path: str) -> None:
        pass

    def set_missing_host_key_policy(self, policy) -> None:
        self.host_key_policy = policy

    def connect(self, **kwargs) -> None:
        if self.connect_error is not None:
            raise self.connect_error
        self.connect_kwargs = kwargs

    def exec_command(self, command: str, timeout: float | None = None):
        self.commands.append(command)
        return None, FakeStdout(self.responses.get(command, "")), FakeStdout("")

    def close(self) -> None:
        self.closed = True


def make_connector(
    responses: dict[str, str] | None = None,
    connect_error: Exception | None = None,
    credentials: dict | None = None,
) -> tuple[SSHConnector, FakeSSHClient]:
    client = FakeSSHClient(responses=responses, connect_error=connect_error)
    connector = SSHConnector(
        "1",
        "10.0.0.1",
        {**CREDENTIALS, **(credentials or {})},
        client_factory=lambda: client,
    )
    return connector, client


class TestHostKeyPolicy:
    async def test_unknown_host_keys_are_rejected_by_default(self):
        """The safe default: an unrecognised key aborts the connection."""
        connector, client = make_connector()

        await connector.connect()

        assert isinstance(client.host_key_policy, paramiko.RejectPolicy)

    async def test_operator_can_opt_into_accepting_unknown_keys(self):
        connector, client = make_connector(
            credentials={"allow_unknown_host_keys": True}
        )

        await connector.connect()

        assert isinstance(client.host_key_policy, paramiko.WarningPolicy)

    async def test_system_host_keys_are_loaded(self):
        connector, client = make_connector()

        await connector.connect()

        assert client.loaded_system_keys is True


class TestConnectionFailures:
    async def test_rejected_credentials_raise_an_auth_error(self):
        """Distinguishable from unreachable: NetVault returned False for both."""
        connector, _ = make_connector(
            connect_error=paramiko.AuthenticationException("bad password")
        )

        with pytest.raises(ConnectorAuthError, match="credentials"):
            await connector.connect()

    async def test_unreachable_host_raises_an_unreachable_error(self):
        connector, _ = make_connector(connect_error=OSError("no route to host"))

        with pytest.raises(ConnectorUnreachableError, match="Cannot reach"):
            await connector.connect()

    async def test_timeout_raises_an_unreachable_error(self):
        connector, _ = make_connector(connect_error=TimeoutError("timed out"))

        with pytest.raises(ConnectorUnreachableError):
            await connector.connect()

    async def test_a_failed_connect_leaves_the_connector_disconnected(self):
        connector, _ = make_connector(connect_error=OSError("down"))

        with pytest.raises(ConnectorUnreachableError):
            await connector.connect()

        assert connector.is_connected is False


class TestConnectionTest:
    async def test_successful_probe_reports_success_and_latency(self):
        connector, _ = make_connector()

        result = await connector.test_connection()

        assert result.success is True
        assert result.latency_ms >= 0

    async def test_failed_probe_carries_the_reason(self):
        connector, _ = make_connector(
            connect_error=paramiko.AuthenticationException("nope")
        )

        result = await connector.test_connection()

        assert result.success is False
        assert "credentials" in result.error_message

    async def test_probe_closes_a_session_it_opened(self):
        connector, _ = make_connector()

        await connector.test_connection()

        assert connector.is_connected is False

    async def test_probe_leaves_an_existing_session_open(self):
        """NetVault disconnected in a finally, killing a live session."""
        connector, _ = make_connector()
        await connector.connect()

        await connector.test_connection()

        assert connector.is_connected is True


class TestLifecycle:
    async def test_connect_is_idempotent(self):
        connector, _ = make_connector()

        await connector.connect()
        await connector.connect()

        assert connector.is_connected is True

    async def test_disconnect_closes_the_client(self):
        connector, client = make_connector()
        await connector.connect()

        await connector.disconnect()

        assert client.closed is True
        assert connector.is_connected is False

    async def test_disconnect_is_safe_when_never_connected(self):
        connector, _ = make_connector()

        await connector.disconnect()

        assert connector.is_connected is False

    async def test_credentials_are_passed_to_paramiko(self):
        connector, client = make_connector()

        await connector.connect()

        assert client.connect_kwargs["hostname"] == "10.0.0.1"
        assert client.connect_kwargs["username"] == "operator"
        assert client.connect_kwargs["password"] == "s3cr3t"
        assert client.connect_kwargs["port"] == 22


class TestMikrotikCollection:
    async def test_system_info_is_parsed(self):
        connector, _ = make_connector({"/system resource print": SYSTEM_RESOURCE})

        info = await connector.get_system_info()

        assert info["model"] == "RB750Gr3"

    async def test_interfaces_are_parsed(self):
        connector, _ = make_connector({"/interface print": INTERFACES})

        interfaces = await connector.get_interfaces()

        assert [i.name for i in interfaces] == ["ether1", "ether2"]

    async def test_arp_table_is_parsed(self):
        connector, _ = make_connector({"/ip arp print": ARP})

        entries = await connector.get_arp_table()

        assert len(entries) == 3

    async def test_mac_table_is_empty_because_routeros_has_no_such_command(self):
        """A router with no MAC table must return nothing, not error."""
        connector, _ = make_connector()

        assert await connector.get_mac_table() == []

    async def test_the_expected_commands_are_issued(self):
        connector, client = make_connector({"/interface print": INTERFACES})

        await connector.get_interfaces()

        assert client.commands == ["/interface print"]


class TestCiscoCollection:
    async def test_system_info_is_parsed(self):
        connector, _ = make_connector(
            {"show version": SHOW_VERSION}, credentials={"device_type": "cisco"}
        )

        info = await connector.get_system_info()

        assert info["model"] == "WS-C2960-24TT-L"

    async def test_interfaces_are_parsed(self):
        connector, _ = make_connector(
            {"show ip interface brief": SHOW_IP_INTERFACE_BRIEF},
            credentials={"device_type": "cisco"},
        )

        interfaces = await connector.get_interfaces()

        assert len(interfaces) == 3


class TestDeviceDetection:
    async def test_routeros_banner_identifies_mikrotik(self):
        connector, _ = make_connector(
            {"/system resource print": SYSTEM_RESOURCE},
            credentials={"device_type": "auto"},
        )

        await connector.connect()

        assert connector.device_type == "mikrotik"

    async def test_cisco_banner_identifies_cisco(self):
        connector, _ = make_connector(
            {"show version": SHOW_VERSION}, credentials={"device_type": "auto"}
        )

        await connector.connect()

        assert connector.device_type == "cisco"

    async def test_unrecognised_device_is_marked_unknown_not_guessed(self):
        """NetVault keyed on the substring 'exec' and mislabelled devices."""
        connector, _ = make_connector(
            {"show version": "Some unrelated appliance, exec mode ready"},
            credentials={"device_type": "auto"},
        )

        await connector.connect()

        assert connector.device_type == "unknown"


class TestUnsupportedDevice:
    async def test_collection_returns_empty_rather_than_raising(self):
        connector, _ = make_connector(credentials={"device_type": "unknown"})

        assert await connector.get_interfaces() == []
        assert await connector.get_arp_table() == []
        assert await connector.get_routes() == []

    async def test_system_info_reports_the_unsupported_type(self):
        connector, _ = make_connector(credentials={"device_type": "unknown"})

        info = await connector.get_system_info()

        assert "Unsupported" in info["error"]


class TestAudit:
    async def test_audit_reports_interface_status(self):
        connector, _ = make_connector(
            {
                "/system resource print": SYSTEM_RESOURCE,
                "/interface print": INTERFACES,
                "/ip arp print": ARP,
            }
        )

        result = await connector.run_audit()
        interface_check = next(c for c in result.checks if c.name == "Interfaces")

        assert interface_check.details["total"] == 2
        assert interface_check.details["down"] == ["ether2"]

    async def test_a_down_interface_raises_a_warning(self):
        connector, _ = make_connector(
            {
                "/system resource print": SYSTEM_RESOURCE,
                "/interface print": INTERFACES,
                "/ip arp print": ARP,
            }
        )

        result = await connector.run_audit()

        assert result.worst_status == "warning"

    async def test_unknown_device_type_warns_instead_of_reporting_a_clean_pass(self):
        """Silence about an unidentified device would read as a healthy result."""
        connector, _ = make_connector(credentials={"device_type": "unknown"})

        result = await connector.run_audit()

        assert result.worst_status == "warning"
        assert "incomplete" in result.summary

    async def test_audit_timestamp_is_timezone_aware(self):
        connector, _ = make_connector(credentials={"device_type": "unknown"})

        result = await connector.run_audit()

        assert result.timestamp.tzinfo is not None


class TestInteractiveOutputCleaning:
    def test_echoed_command_and_prompt_are_removed(self):
        raw = "/system resource print\r\n  uptime: 1d\r\n[admin@router] > "

        cleaned = SSHConnector.clean_interactive_output(
            raw, "/system resource print", ">"
        )

        assert cleaned == "uptime: 1d"

    def test_login_noise_is_removed(self):
        raw = "Login: operator\r\nPassword:\r\nversion: 7.12\r\n#"

        cleaned = SSHConnector.clean_interactive_output(raw, "version", "#")

        assert cleaned == "version: 7.12"

    def test_empty_output_stays_empty(self):
        assert SSHConnector.clean_interactive_output("", "cmd", "#") == ""


class TestRegistration:
    def test_the_connector_registers_itself_as_ssh(self):
        from lynjax.services.connectors.base import get_connector

        assert get_connector("ssh") is SSHConnector
