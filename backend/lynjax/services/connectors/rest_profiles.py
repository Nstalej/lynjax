"""Vendor profiles for the REST connector.

A profile knows how to ask one family of device for data and how to read the
answer. The connector handles transport, retries and auth; profiles handle
shape.

Ported from NetVault's ``connectors/rest_api/profiles``. The significant change
is that Sophos request bodies are now escaped. NetVault built its login XML with
an f-string, so a password containing ``<`` or ``&`` produced malformed XML, and
a crafted value could inject arbitrary elements into the request.
"""

from __future__ import annotations

from typing import Any, Protocol
from xml.sax.saxutils import escape as xml_escape

from lynjax.services.connectors.base import (
    ArpEntry,
    InterfaceInfo,
    RouteEntry,
    normalize_mac,
)

TRUTHY_STATUS = {"up", "online", "connected", "1", "true", "enabled"}


def _status_from(value: Any) -> str:
    """Map a vendor's notion of "working" onto the shared status vocabulary."""
    if isinstance(value, bool):
        return "up" if value else "down"
    if isinstance(value, int):
        return "up" if value == 1 else "down"
    if value is None:
        return "unknown"
    return "up" if str(value).strip().lower() in TRUTHY_STATUS else "down"


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class RestProfile(Protocol):
    """What the REST connector needs from a vendor profile."""

    name: str

    def endpoint(self, key: str) -> str | None:
        """Path for a capability, or None when this device cannot serve it."""
        ...


class GenericJsonProfile:
    """Configurable profile for any device that returns JSON.

    Endpoints are supplied per device, so an appliance with its own API can be
    described in credentials rather than needing code.
    """

    name = "generic"

    def __init__(self, endpoints: dict[str, str] | None = None) -> None:
        self.endpoints = endpoints or {}

    def endpoint(self, key: str) -> str | None:
        return self.endpoints.get(key)

    @staticmethod
    def parse_system_info(data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {"model": "Generic", "os_version": "Unknown"}
        return {
            "model": data.get("model") or data.get("device_model") or "Generic",
            "os_version": data.get("os_version") or data.get("firmware") or "Unknown",
            "uptime": data.get("uptime") or "Unknown",
        }

    @staticmethod
    def parse_interfaces(data: Any) -> list[InterfaceInfo]:
        if not isinstance(data, list):
            return []

        interfaces: list[InterfaceInfo] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            raw_mac = item.get("mac_address") or item.get("mac")
            interfaces.append(
                InterfaceInfo(
                    name=str(item.get("name") or item.get("index") or "unknown"),
                    status=_status_from(item.get("status")),
                    ip=item.get("ip_address") or item.get("ip"),
                    mac=normalize_mac(raw_mac) if raw_mac else None,
                    rx_bytes=_as_int(item.get("rx_bytes")),
                    tx_bytes=_as_int(item.get("tx_bytes")),
                    errors=_as_int(item.get("errors")),
                )
            )
        return interfaces

    @staticmethod
    def parse_arp_table(data: Any) -> list[ArpEntry]:
        if not isinstance(data, list):
            return []

        entries: list[ArpEntry] = []
        for item in data:
            if not isinstance(item, dict) or not item.get("ip"):
                continue
            entries.append(
                ArpEntry(
                    ip=str(item["ip"]),
                    mac=normalize_mac(str(item.get("mac", ""))),
                    interface=str(item.get("interface") or ""),
                    type="static" if item.get("type") == "static" else "dynamic",
                )
            )
        return entries

    @staticmethod
    def parse_routes(data: Any) -> list[RouteEntry]:
        """Parse routes from JSON.

        NetVault declared this endpoint and then returned an empty list with a
        "not implemented yet" comment, so a configured route endpoint produced
        silence that read as "this device has no routes".
        """
        if not isinstance(data, list):
            return []

        routes: list[RouteEntry] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            destination = item.get("destination") or item.get("network")
            if not destination:
                continue
            routes.append(
                RouteEntry(
                    destination=str(destination),
                    gateway=str(item.get("gateway") or item.get("next_hop") or ""),
                    interface=str(item.get("interface") or ""),
                    metric=_as_int(item.get("metric")),
                    protocol=str(item.get("protocol") or "unknown"),
                )
            )
        return routes


class SophosProfile:
    """Sophos XG/XGS, which speaks XML over a POST to a single controller path."""

    name = "sophos"
    API_PATH = "/webconsole/APIController"
    DEFAULT_PORT = 4444

    #: Capability to Sophos entity name.
    ENTITIES = {
        "system": "SystemStatus",
        "interfaces": "Interface",
        "arp": "ARPTable",
        "routes": "RoutingTable",
    }

    def endpoint(self, key: str) -> str | None:
        return self.API_PATH if key in self.ENTITIES else None

    def build_request(self, username: str, password: str, capability: str) -> str:
        """Build a Sophos request body.

        Credentials are XML-escaped. NetVault interpolated them raw, so a
        password containing ``<`` or ``&`` produced malformed XML and a crafted
        value could inject elements into the request.
        """
        entity = self.ENTITIES.get(capability)
        if entity is None:
            raise ValueError(f"Sophos profile has no entity for {capability!r}")

        return (
            "<Request>"
            "<Login>"
            f"<UserName>{xml_escape(username)}</UserName>"
            f"<Password>{xml_escape(password)}</Password>"
            "</Login>"
            f"<Get><{entity}></{entity}></Get>"
            "</Request>"
        )

    @staticmethod
    def _parse_xml(content: bytes):
        from lxml import etree

        # resolve_entities=False blocks XXE: a hostile response must not be able
        # to make the parser read local files or reach out over the network.
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        return etree.fromstring(content, parser=parser)

    @classmethod
    def parse_system_info(cls, content: bytes) -> dict[str, Any]:
        root = cls._parse_xml(content)
        return {
            "model": root.xpath("string(//Model)") or "Sophos",
            "os_version": root.xpath("string(//FirmwareVersion)") or "Unknown",
            "uptime": root.xpath("string(//Uptime)") or "Unknown",
            "vendor": "sophos",
        }

    @classmethod
    def parse_interfaces(cls, content: bytes) -> list[InterfaceInfo]:
        root = cls._parse_xml(content)
        interfaces: list[InterfaceInfo] = []

        for node in root.xpath("//Interface"):
            raw_mac = node.xpath("string(MACAddress)")
            interfaces.append(
                InterfaceInfo(
                    name=node.xpath("string(Name)"),
                    status=_status_from(node.xpath("string(Status)")),
                    ip=node.xpath("string(IPAddress)") or None,
                    mac=normalize_mac(raw_mac) if raw_mac else None,
                    rx_bytes=_as_int(node.xpath("string(RxBytes)")),
                    tx_bytes=_as_int(node.xpath("string(TxBytes)")),
                )
            )
        return interfaces

    @classmethod
    def parse_arp_table(cls, content: bytes) -> list[ArpEntry]:
        root = cls._parse_xml(content)
        entries: list[ArpEntry] = []

        for node in root.xpath("//ARPEntry"):
            ip = node.xpath("string(IPAddress)")
            if not ip:
                continue
            entries.append(
                ArpEntry(
                    ip=ip,
                    mac=normalize_mac(node.xpath("string(MACAddress)")),
                    interface=node.xpath("string(Interface)"),
                    type="static"
                    if node.xpath("string(Type)").lower() == "static"
                    else "dynamic",
                )
            )
        return entries

    @classmethod
    def parse_routes(cls, content: bytes) -> list[RouteEntry]:
        root = cls._parse_xml(content)
        routes: list[RouteEntry] = []

        for node in root.xpath("//Route"):
            destination = node.xpath("string(Destination)")
            if not destination:
                continue
            routes.append(
                RouteEntry(
                    destination=destination,
                    gateway=node.xpath("string(Gateway)"),
                    interface=node.xpath("string(Interface)"),
                    metric=_as_int(node.xpath("string(Metric)")),
                    protocol=node.xpath("string(Protocol)") or "static",
                )
            )
        return routes


def get_profile(name: str, endpoints: dict[str, str] | None = None):
    """Return the profile for ``name``, defaulting to the generic JSON one."""
    if (name or "").strip().lower() == "sophos":
        return SophosProfile()
    return GenericJsonProfile(endpoints)
