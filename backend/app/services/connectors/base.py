"""Connector contract and shared data structures.

Ported from NetVault's ``connectors/base.py``. Changes worth knowing about:

* ``AuditResult.timestamp`` now defaults to an aware UTC datetime.
  NetVault used ``datetime.utcnow``, which returns a naive value and broke
  comparisons against the aware timestamps used everywhere else.
* MAC normalisation lives here instead of being reimplemented inside each
  parser, so ``00aa.bbcc.ddee`` and ``00-AA-BB-CC-DD-EE`` cannot end up as two
  different devices in the same audit.
* Structures are frozen. Parser output is a snapshot of what a device reported;
  nothing downstream should be rewriting it in place.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

CheckStatus = Literal["pass", "warning", "fail"]
InterfaceStatus = Literal["up", "down", "unknown"]
EntryType = Literal["static", "dynamic", "learned", "unknown"]

_MAC_SEPARATORS = re.compile(r"[.:\-\s]")


def utc_now() -> datetime:
    """Aware UTC timestamp. Never use ``datetime.utcnow``, which is naive."""
    return datetime.now(timezone.utc)


def normalize_mac(raw: str) -> str:
    """Return a MAC as upper-case colon-separated octets.

    Accepts the three vendor spellings seen in the field: Cisco's
    ``00aa.bbcc.ddee``, Windows' ``00-AA-BB-CC-DD-EE`` and the common
    ``00:aa:bb:cc:dd:ee``. Anything that is not twelve hex digits is returned
    stripped but otherwise untouched, so unexpected input stays visible in the
    report instead of being silently mangled.
    """
    if not raw:
        return ""

    digits = _MAC_SEPARATORS.sub("", raw).strip()
    if len(digits) != 12 or not all(
        char in "0123456789abcdefABCDEF" for char in digits
    ):
        return raw.strip()

    return ":".join(digits[i : i + 2] for i in range(0, 12, 2)).upper()


@dataclass(frozen=True)
class ConnectionTestResult:
    success: bool
    latency_ms: float
    error_message: str | None = None


@dataclass(frozen=True)
class InterfaceInfo:
    name: str
    status: InterfaceStatus
    speed: int | None = None
    mac: str | None = None
    ip: str | None = None
    rx_bytes: int = 0
    tx_bytes: int = 0
    errors: int = 0


@dataclass(frozen=True)
class ArpEntry:
    ip: str
    mac: str
    interface: str
    type: EntryType


@dataclass(frozen=True)
class MacEntry:
    mac: str
    port: str
    vlan: int
    type: EntryType


@dataclass(frozen=True)
class RouteEntry:
    destination: str
    gateway: str
    interface: str
    metric: int
    protocol: str


@dataclass(frozen=True)
class AuditCheck:
    name: str
    status: CheckStatus
    message: str
    details: dict[str, Any] | None = None


@dataclass
class AuditResult:
    device_name: str
    timestamp: datetime = field(default_factory=utc_now)
    checks: list[AuditCheck] = field(default_factory=list)
    summary: str = ""

    @property
    def worst_status(self) -> CheckStatus:
        """The most severe status across all checks."""
        statuses = {check.status for check in self.checks}
        if "fail" in statuses:
            return "fail"
        if "warning" in statuses:
            return "warning"
        return "pass"


class ConnectorError(RuntimeError):
    """Base class for connector failures."""


class ConnectorAuthError(ConnectorError):
    """Credentials were rejected by the device."""


class ConnectorUnreachableError(ConnectorError):
    """The device could not be reached."""


class BaseConnector(ABC):
    """Contract every device connector implements.

    Connectors are per-device and stateful: ``connect`` opens a session,
    ``disconnect`` closes it. Implementations must tolerate ``disconnect``
    being called when never connected.
    """

    def __init__(
        self, device_id: str, device_ip: str, credentials: dict[str, Any]
    ) -> None:
        self.device_id = device_id
        self.device_ip = device_ip
        self.credentials = credentials
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def __aenter__(self) -> BaseConnector:
        await self.connect()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.disconnect()

    @abstractmethod
    async def connect(self) -> bool:
        """Open a session. Returns True on success."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the session. Safe to call when not connected."""

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Probe reachability and credentials without collecting data."""

    @abstractmethod
    async def get_system_info(self) -> dict[str, Any]:
        """Model, OS version, uptime and similar identity fields."""

    @abstractmethod
    async def get_interfaces(self) -> list[InterfaceInfo]:
        """Interface inventory with operational status."""

    async def get_arp_table(self) -> list[ArpEntry]:
        """ARP entries. Empty when the device type has no ARP table."""
        return []

    async def get_mac_table(self) -> list[MacEntry]:
        """MAC address table. Empty for devices that do not switch."""
        return []

    async def get_routes(self) -> list[RouteEntry]:
        """Routing table. Empty for devices that do not route."""
        return []

    @abstractmethod
    async def run_audit(self) -> AuditResult:
        """Run the connector's checks against the device."""


#: Registry of connector implementations, keyed by the name used in device
#: records. Populated by ``register_connector`` at import time.
_REGISTRY: dict[str, type[BaseConnector]] = {}


def register_connector(name: str, connector_cls: type[BaseConnector]) -> None:
    """Register a connector implementation under a device-record name."""
    _REGISTRY[name.lower()] = connector_cls


def get_connector(name: str) -> type[BaseConnector] | None:
    """Look up a connector class, or None when the name is unknown."""
    return _REGISTRY.get((name or "").lower())


def available_connectors() -> list[str]:
    """Names of every registered connector, sorted."""
    return sorted(_REGISTRY)
