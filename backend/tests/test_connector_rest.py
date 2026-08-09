"""Tests for the REST connector and its vendor profiles."""

from __future__ import annotations

import httpx
import pytest

from app.services.connectors.base import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorUnreachableError,
)
from app.services.connectors.rest import RESTConnector
from app.services.connectors.rest_profiles import (
    GenericJsonProfile,
    SophosProfile,
    get_profile,
)

SOPHOS_INTERFACES = b"""<Response>
  <Interface>
    <Name>Port1</Name><Status>1</Status>
    <IPAddress>10.0.0.1</IPAddress><MACAddress>00aa.bbcc.ddee</MACAddress>
    <RxBytes>1000</RxBytes><TxBytes>2000</TxBytes>
  </Interface>
  <Interface>
    <Name>Port2</Name><Status>0</Status>
  </Interface>
</Response>"""

SOPHOS_SYSTEM = b"""<Response>
  <Model>XGS 2100</Model><FirmwareVersion>19.5.3</FirmwareVersion>
  <Uptime>10 days</Uptime>
</Response>"""


def make_connector(handler, credentials=None):
    """Build a connector whose HTTP client is backed by a mock transport."""
    transport = httpx.MockTransport(handler)

    def factory(**kwargs):
        kwargs.pop("verify", None)
        return httpx.AsyncClient(transport=transport, **kwargs)

    return RESTConnector(
        "1",
        "10.0.0.1",
        {
            "auth_type": "basic",
            "username": "op",
            "password": "pw",
            **(credentials or {}),
        },
        client_factory=factory,
    )


class TestSophosRequestEscaping:
    def test_credentials_are_xml_escaped(self):
        """NetVault interpolated these raw, so `<` broke the request body."""
        body = SophosProfile().build_request("op<er>", "p&w'd", "system")

        assert "op&lt;er&gt;" in body
        assert "p&amp;w" in body
        assert "<UserName>op<er>" not in body

    def test_a_password_cannot_inject_elements(self):
        body = SophosProfile().build_request(
            "op", "</Password><Injected>evil</Injected><Password>", "system"
        )

        assert "<Injected>" not in body

    def test_an_unknown_capability_is_rejected(self):
        with pytest.raises(ValueError, match="no entity"):
            SophosProfile().build_request("op", "pw", "telepathy")


class TestSophosParsing:
    def test_interfaces_are_parsed_with_normalised_macs(self):
        interfaces = SophosProfile.parse_interfaces(SOPHOS_INTERFACES)

        assert [i.name for i in interfaces] == ["Port1", "Port2"]
        assert interfaces[0].status == "up"
        assert interfaces[0].mac == "00:AA:BB:CC:DD:EE"
        assert interfaces[1].status == "down"

    def test_system_info_is_parsed(self):
        info = SophosProfile.parse_system_info(SOPHOS_SYSTEM)

        assert info["model"] == "XGS 2100"
        assert info["os_version"] == "19.5.3"

    def test_external_entities_are_not_resolved(self):
        """A hostile response must not make the parser read local files."""
        hostile = (
            b'<?xml version="1.0"?>'
            b'<!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            b"<Response><Model>&xxe;</Model></Response>"
        )

        info = SophosProfile.parse_system_info(hostile)

        assert "root:" not in info["model"]


class TestGenericProfile:
    def test_endpoints_come_from_configuration(self):
        profile = GenericJsonProfile({"system": "/api/status"})

        assert profile.endpoint("system") == "/api/status"
        assert profile.endpoint("arp") is None

    def test_interfaces_are_parsed(self):
        interfaces = GenericJsonProfile.parse_interfaces(
            [{"name": "eth0", "status": "up", "mac_address": "00-AA-BB-CC-DD-EE"}]
        )

        assert interfaces[0].mac == "00:AA:BB:CC:DD:EE"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("up", "up"), ("online", "up"), (1, "up"), (True, "up"), ("down", "down")],
    )
    def test_vendor_status_spellings_are_mapped(self, value, expected):
        interfaces = GenericJsonProfile.parse_interfaces(
            [{"name": "eth0", "status": value}]
        )

        assert interfaces[0].status == expected

    def test_routes_are_actually_parsed(self):
        """NetVault returned [] here with a "not implemented" comment, so a
        configured route endpoint produced silence that read as "no routes"."""
        routes = GenericJsonProfile.parse_routes(
            [{"destination": "0.0.0.0/0", "gateway": "10.0.0.254", "metric": 1}]
        )

        assert routes[0].destination == "0.0.0.0/0"
        assert routes[0].gateway == "10.0.0.254"

    def test_malformed_payloads_yield_nothing_rather_than_raising(self):
        assert GenericJsonProfile.parse_interfaces({"not": "a list"}) == []
        assert GenericJsonProfile.parse_arp_table("nonsense") == []

    def test_get_profile_selects_sophos_case_insensitively(self):
        assert isinstance(get_profile("Sophos"), SophosProfile)

    def test_get_profile_defaults_to_generic(self):
        assert isinstance(get_profile("anything-else"), GenericJsonProfile)


class TestRequests:
    async def test_a_successful_request_returns_parsed_json(self):
        def handler(request):
            return httpx.Response(200, json={"model": "FW-100", "firmware": "2.1"})

        connector = make_connector(handler, {"endpoints": {"system": "/api/system"}})

        info = await connector.get_system_info()
        await connector.disconnect()

        assert info["model"] == "FW-100"

    async def test_rejected_credentials_raise_an_auth_error(self):
        def handler(request):
            return httpx.Response(401)

        connector = make_connector(handler, {"endpoints": {"system": "/api/system"}})

        with pytest.raises(ConnectorAuthError, match="credentials"):
            await connector.get_system_info()
        await connector.disconnect()

    async def test_a_403_is_also_an_auth_error(self):
        def handler(request):
            return httpx.Response(403)

        connector = make_connector(handler, {"endpoints": {"system": "/api/system"}})

        with pytest.raises(ConnectorAuthError):
            await connector.get_system_info()
        await connector.disconnect()

    async def test_a_transport_failure_is_reported_as_unreachable(self):
        def handler(request):
            raise httpx.ConnectError("no route to host")

        connector = make_connector(
            handler,
            {"endpoints": {"system": "/api/system"}, "max_retries": 1},
        )

        with pytest.raises(ConnectorUnreachableError, match="Cannot reach"):
            await connector.get_system_info()
        await connector.disconnect()

    async def test_a_retryable_status_is_retried_then_succeeds(self):
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(503)
            return httpx.Response(200, json={"model": "FW"})

        connector = make_connector(
            handler,
            {
                "endpoints": {"system": "/api/system"},
                "max_retries": 2,
                "retry_backoff": 0,
            },
        )

        info = await connector.get_system_info()
        await connector.disconnect()

        assert calls["n"] == 2
        assert info["model"] == "FW"

    async def test_a_client_error_is_not_retried(self):
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            return httpx.Response(404)

        connector = make_connector(
            handler, {"endpoints": {"system": "/api/system"}, "retry_backoff": 0}
        )

        with pytest.raises(ConnectorError, match="404"):
            await connector.get_system_info()
        await connector.disconnect()

        assert calls["n"] == 1

    async def test_non_json_is_reported_clearly(self):
        def handler(request):
            return httpx.Response(200, text="<html>login page</html>")

        connector = make_connector(handler, {"endpoints": {"system": "/api/system"}})

        with pytest.raises(ConnectorError, match="did not return JSON"):
            await connector.get_system_info()
        await connector.disconnect()

    async def test_the_api_key_is_sent_as_a_header(self):
        seen = {}

        def handler(request):
            seen.update(request.headers)
            return httpx.Response(200, json={})

        connector = make_connector(
            handler,
            {
                "auth_type": "api_key",
                "api_key": "k3y",
                "endpoints": {"system": "/api/system"},
            },
        )

        await connector.get_system_info()
        await connector.disconnect()

        assert seen["x-api-key"] == "k3y"


class TestPorts:
    def test_sophos_defaults_to_its_management_port(self):
        connector = make_connector(
            lambda r: httpx.Response(200), {"rest_profile": "sophos"}
        )

        assert connector.port == 4444

    def test_https_defaults_to_443(self):
        connector = make_connector(lambda r: httpx.Response(200))

        assert connector.port == 443

    def test_an_explicit_port_wins(self):
        connector = make_connector(lambda r: httpx.Response(200), {"port": 8443})

        assert connector.base_url.endswith(":8443")


class TestAudit:
    async def test_disabled_certificate_verification_is_a_failure(self):
        def handler(request):
            return httpx.Response(200, json={"model": "FW"})

        connector = make_connector(
            handler, {"verify_ssl": False, "endpoints": {"system": "/api/system"}}
        )

        result = await connector.run_audit()
        await connector.disconnect()

        check = next(c for c in result.checks if "certificate" in c.name.lower())
        assert check.status == "fail"

    async def test_plain_http_management_is_a_failure(self):
        def handler(request):
            return httpx.Response(200, json={"model": "FW"})

        connector = make_connector(
            handler, {"protocol": "http", "endpoints": {"system": "/api/system"}}
        )

        result = await connector.run_audit()
        await connector.disconnect()

        assert any(c.name == "Transport" and c.status == "fail" for c in result.checks)

    async def test_an_unreachable_device_reports_failure_not_silence(self):
        """NetVault swallowed this and reported a device with no findings."""

        def handler(request):
            raise httpx.ConnectError("down")

        connector = make_connector(
            handler,
            {"endpoints": {"system": "/api/system"}, "max_retries": 1},
        )

        result = await connector.run_audit()
        await connector.disconnect()

        assert result.worst_status == "fail"
        assert "incomplete" in result.summary


class TestRegistration:
    def test_it_registers_under_rest(self):
        from app.services.connectors.base import get_connector

        assert get_connector("rest") is RESTConnector

    def test_the_netvault_name_still_resolves(self):
        """Existing inventories say rest_api; they must keep working."""
        from app.services.connectors.base import get_connector

        assert get_connector("rest_api") is RESTConnector
