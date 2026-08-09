"""REST connector for appliances with an HTTP API.

Ported from NetVault's ``RESTConnector``. Changes worth knowing:

* **Collection failures are no longer swallowed.** Every collector in NetVault
  wrapped its body in ``except Exception`` and returned ``[]`` or ``{}``, so an
  unreachable firewall produced "no interfaces, no routes, no ARP entries" —
  which downstream reads as a device with nothing wrong. Failures now raise.
* **The HTTP client is injectable**, so the request path is tested without a
  server.
* **``test_connection`` releases the client it opened.** NetVault's leaked one
  per probe.
* **Credentials are escaped** before going into a Sophos request body; see
  ``rest_profiles``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from lynjax.services.connectors.base import (
    ArpEntry,
    AuditCheck,
    AuditResult,
    BaseConnector,
    ConnectionTestResult,
    ConnectorAuthError,
    ConnectorError,
    ConnectorUnreachableError,
    InterfaceInfo,
    RouteEntry,
    register_connector,
)
from lynjax.services.connectors.rest_profiles import (
    SophosProfile,
    get_profile,
)

logger = logging.getLogger("lynjax.connectors.rest")

#: Status codes worth retrying: the device is up but asking us to back off.
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


class RESTConnector(BaseConnector):
    """Collects device state over an HTTP API."""

    def __init__(
        self,
        device_id: str,
        device_ip: str,
        credentials: dict[str, Any],
        *,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        super().__init__(device_id, device_ip, credentials)

        self.protocol = credentials.get("protocol", "https")
        self.verify_ssl = bool(credentials.get("verify_ssl", True))
        self.timeout = float(credentials.get("timeout", 15))
        self.max_retries = max(1, int(credentials.get("max_retries", 3)))
        self.retry_backoff = float(credentials.get("retry_backoff", 2))

        self.auth_type = str(credentials.get("auth_type", "none")).lower()
        self.api_key = credentials.get("api_key")
        self.api_key_location = credentials.get("api_key_location", "header")
        self.api_key_name = (
            credentials.get("api_key_header")
            or credentials.get("api_key_name")
            or "X-API-Key"
        )

        self.profile = get_profile(
            credentials.get("rest_profile", "generic"), credentials.get("endpoints")
        )

        port = credentials.get("port")
        if not port and isinstance(self.profile, SophosProfile):
            port = SophosProfile.DEFAULT_PORT

        self.port = int(port) if port else (443 if self.protocol == "https" else 80)
        self.base_url = f"{self.protocol}://{self.device_ip}:{self.port}"

        self._client_factory = client_factory
        self._client: httpx.AsyncClient | None = None

    # ─── Lifecycle ───

    async def connect(self) -> bool:
        if self._client is None:
            self._client = self._client_factory(
                verify=self.verify_ssl,
                timeout=self.timeout,
                follow_redirects=True,
            )
        self._is_connected = True
        return True

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._is_connected = False

    async def test_connection(self) -> ConnectionTestResult:
        """Probe the API, leaving any session the caller already opened alone."""
        was_connected = self._is_connected
        start = time.perf_counter()

        try:
            await self.get_system_info()
            return ConnectionTestResult(
                success=True, latency_ms=(time.perf_counter() - start) * 1000
            )
        except ConnectorError as exc:
            return ConnectionTestResult(
                success=False,
                latency_ms=(time.perf_counter() - start) * 1000,
                error_message=str(exc),
            )
        finally:
            if not was_connected:
                await self.disconnect()

    # ─── Requests ───

    def _auth(self) -> dict[str, Any]:
        headers: dict[str, str] = {}
        params: dict[str, str] = {}
        auth = None

        if self.auth_type == "basic":
            auth = (
                self.credentials.get("username", ""),
                self.credentials.get("password", ""),
            )
        elif self.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.credentials.get('token', '')}"
        elif self.auth_type == "api_key" and self.api_key:
            if self.api_key_location == "header":
                headers[self.api_key_name] = self.api_key
            else:
                params[self.api_key_name] = self.api_key

        return {"headers": headers, "params": params, "auth": auth}

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Issue a request, retrying only what is worth retrying."""
        if self._client is None:
            await self.connect()
        assert self._client is not None

        auth = self._auth()
        kwargs["headers"] = {**auth["headers"], **kwargs.get("headers", {})}
        kwargs["params"] = {**auth["params"], **kwargs.get("params", {})}
        if auth["auth"] is not None:
            kwargs.setdefault("auth", auth["auth"])

        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                await asyncio.sleep(self.retry_backoff * attempt)
                continue

            if response.status_code in {401, 403}:
                raise ConnectorAuthError(
                    f"{self.device_ip} rejected the supplied credentials "
                    f"(HTTP {response.status_code})"
                )

            if response.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                logger.warning(
                    "%s returned %s, retrying (%s/%s)",
                    url,
                    response.status_code,
                    attempt,
                    self.max_retries,
                )
                await asyncio.sleep(self.retry_backoff * attempt)
                continue

            if response.status_code >= 400:
                raise ConnectorError(f"{url} returned HTTP {response.status_code}")

            return response

        raise ConnectorUnreachableError(
            f"Cannot reach {url} after {self.max_retries} attempt(s): {last_error}"
        )

    async def _fetch(self, capability: str) -> Any | None:
        """Fetch one capability, or None when this profile cannot serve it."""
        path = self.profile.endpoint(capability)
        if path is None:
            return None

        if isinstance(self.profile, SophosProfile):
            body = self.profile.build_request(
                self.credentials.get("username", ""),
                self.credentials.get("password", ""),
                capability,
            )
            response = await self.request(
                "POST", path, content=body, headers={"Content-Type": "application/xml"}
            )
            return response.content

        response = await self.request("GET", path)
        try:
            return response.json()
        except ValueError as exc:
            raise ConnectorError(f"{self.base_url}{path} did not return JSON") from exc

    # ─── Collection ───

    async def get_system_info(self) -> dict[str, Any]:
        payload = await self._fetch("system")
        if payload is None:
            return {"model": "Generic HTTP", "os_version": "Unknown"}
        return self.profile.parse_system_info(payload)

    async def get_interfaces(self) -> list[InterfaceInfo]:
        payload = await self._fetch("interfaces")
        return [] if payload is None else self.profile.parse_interfaces(payload)

    async def get_arp_table(self) -> list[ArpEntry]:
        payload = await self._fetch("arp")
        return [] if payload is None else self.profile.parse_arp_table(payload)

    async def get_routes(self) -> list[RouteEntry]:
        payload = await self._fetch("routes")
        return [] if payload is None else self.profile.parse_routes(payload)

    # ─── Audit ───

    async def run_audit(self) -> AuditResult:
        result = AuditResult(device_name=self.device_ip)

        result.checks.append(
            AuditCheck(
                name="TLS certificate verification",
                status="pass" if self.verify_ssl else "fail",
                message=(
                    "Certificate verification is enabled."
                    if self.verify_ssl
                    else "Certificate verification is disabled, so this session "
                    "can be intercepted. Credentials cross it in clear."
                ),
                details={"verify_ssl": self.verify_ssl},
            )
        )

        if self.protocol != "https":
            result.checks.append(
                AuditCheck(
                    name="Transport",
                    status="fail",
                    message=(
                        "The management API is reached over plain HTTP; "
                        "credentials are sent unencrypted."
                    ),
                )
            )

        try:
            info = await self.get_system_info()
            result.checks.append(
                AuditCheck(
                    name="Management API",
                    status="pass",
                    message=(
                        f"{info.get('model', 'Unknown')} running "
                        f"{info.get('os_version', 'Unknown')}"
                    ),
                    details=info,
                )
            )
        except ConnectorError as exc:
            # Reported rather than swallowed: NetVault returned {} here, and a
            # device that could not be reached looked like a device with no
            # findings.
            result.checks.append(
                AuditCheck(
                    name="Management API",
                    status="fail",
                    message=f"Could not collect system information: {exc}",
                )
            )
            result.summary = f"Audit incomplete for {self.device_ip}."
            return result

        interfaces = await self.get_interfaces()
        if interfaces:
            down = [item for item in interfaces if item.status != "up"]
            result.checks.append(
                AuditCheck(
                    name="Interfaces",
                    status="warning" if down else "pass",
                    message=(
                        f"{len(interfaces) - len(down)} of {len(interfaces)} "
                        f"interfaces are up."
                    ),
                    details={"down": [item.name for item in down]},
                )
            )

        result.summary = (
            f"{len(result.checks)} checks run against {self.device_ip} over "
            f"the {self.profile.name} REST profile."
        )
        return result


register_connector("rest", RESTConnector)
# NetVault registered this as "rest_api"; kept so existing inventories resolve.
register_connector("rest_api", RESTConnector)
