"""SNMP connector for v2c and v3 devices.

Ported from NetVault's ``SNMPConnector``. The transport is separated from the
table-assembly logic: the functions that turn walk output into structures are
pure, so they are tested directly, and the connector takes a transport object
that the suite replaces with a fake. NetVault embedded pysnmp calls throughout
the class and could not be tested at all.

Bugs found in the original and fixed here:

* ``get_interfaces`` could never run. It resolved column OIDs with
  ``getattr(oids, f"IF_{key.upper()}")`` for keys including ``name``, ``status``,
  ``mac`` and ``errors``, none of which existed in the OID module, so the very
  first iteration raised ``AttributeError``. SNMP interface collection was
  broken for the entire life of the project.
* ``sha256`` mapped to ``usmHMAC128SHA224AuthProtocol``, which is SHA-224. An
  operator asking for SHA-256 silently got a weaker digest.
* ARP entries were all hardcoded as ``dynamic`` even though
  ``ipNetToMediaType`` was already in the OID catalogue. A static ARP binding,
  which is exactly what an audit should notice, was indistinguishable.
* Route metric and protocol were hardcoded to ``0`` and ``"unknown"`` while
  ``ipRouteMetric1`` and ``ipRouteProto`` sat unused.
* Interface speed read only ``ifSpeed``, a 32-bit gauge that saturates at
  ~4.29 Gbps, so every 10G port reported the same wrong number.
* MAC addresses were emitted lowercase and unnormalised, so the same device
  seen over SNMP and over SSH did not correlate.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from app.services.connectors import snmp_oids as oids
from app.services.connectors.base import (
    ArpEntry,
    AuditCheck,
    AuditResult,
    BaseConnector,
    ConnectionTestResult,
    ConnectorError,
    InterfaceInfo,
    MacEntry,
    RouteEntry,
    normalize_mac,
    register_connector,
)

logger = logging.getLogger("lynjax.connectors.snmp")

#: Community strings shipped as defaults by most vendors.
WEAK_COMMUNITIES = frozenset({"public", "private", "admin", "cisco", "manager"})

WalkRow = tuple[str, Any]


class SnmpTransport(Protocol):
    """The two SNMP operations the connector needs."""

    async def get(self, oid: str) -> Any | None:
        """Fetch one scalar OID, or None when it is unavailable."""
        ...

    async def walk(self, base_oid: str) -> list[WalkRow]:
        """Walk a table column, returning (oid, value) rows."""
        ...

    async def close(self) -> None:
        """Release transport resources."""
        ...


# ─── Pure helpers ───


def oid_suffix(oid: str, base: str) -> str:
    """Return the index portion of a table OID."""
    if oid.startswith(base + "."):
        return oid[len(base) + 1 :]
    return oid


def octets_to_mac(value: Any) -> str:
    """Render an SNMP OctetString as a normalised MAC address."""
    as_octets = getattr(value, "asOctets", None)
    if callable(as_octets):
        try:
            return normalize_mac(":".join(f"{byte:02x}" for byte in as_octets()))
        except (TypeError, ValueError):
            pass
    return normalize_mac(str(value))


def oid_tail_to_mac(oid: str, count: int = 6) -> str:
    """Build a MAC from the trailing decimal components of an OID."""
    parts = oid.split(".")[-count:]
    try:
        return normalize_mac(":".join(f"{int(part):02x}" for part in parts))
    except ValueError:
        return ""


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_interfaces(columns: dict[str, list[WalkRow]]) -> list[InterfaceInfo]:
    """Assemble ifTable columns into interfaces, keyed by ifIndex.

    ``columns`` maps a logical name to the rows walked for that column. Missing
    columns are tolerated: a device that does not implement ifXTable still
    yields usable interfaces.
    """
    bases = {
        "descr": oids.IF_DESCR,
        "name": oids.IF_NAME,
        "oper_status": oids.IF_OPER_STATUS,
        "speed": oids.IF_SPEED,
        "high_speed": oids.IF_HIGH_SPEED,
        "mac": oids.IF_PHYS_ADDRESS,
        "in_octets": oids.IF_IN_OCTETS,
        "out_octets": oids.IF_OUT_OCTETS,
        "in_errors": oids.IF_IN_ERRORS,
    }

    by_index: dict[str, dict[str, Any]] = {}
    for key, rows in columns.items():
        base = bases.get(key)
        if base is None:
            continue
        for oid, value in rows:
            index = oid_suffix(oid, base)
            by_index.setdefault(index, {})[key] = value

    interfaces: list[InterfaceInfo] = []
    for index in sorted(by_index, key=lambda item: _as_int(item, 0)):
        data = by_index[index]

        status_code = _as_int(data.get("oper_status"), 4)
        status_name = oids.IF_OPER_STATUS_NAMES.get(status_code, "unknown")
        if status_name == "up":
            status = "up"
        elif status_name in {"unknown", "testing"}:
            status = "unknown"
        else:
            status = "down"

        # ifHighSpeed is in Mbps; convert to bits per second to match ifSpeed.
        high_speed = _as_int(data.get("high_speed"), 0)
        speed = high_speed * 1_000_000 if high_speed else _as_int(data.get("speed"), 0)

        raw_mac = data.get("mac")
        name = data.get("name") or data.get("descr") or f"if-{index}"

        interfaces.append(
            InterfaceInfo(
                name=str(name),
                status=status,
                speed=speed or None,
                mac=octets_to_mac(raw_mac) if raw_mac is not None else None,
                rx_bytes=_as_int(data.get("in_octets")),
                tx_bytes=_as_int(data.get("out_octets")),
                errors=_as_int(data.get("in_errors")),
            )
        )

    return interfaces


def build_arp_entries(
    phys_rows: list[WalkRow], type_rows: list[WalkRow] | None = None
) -> list[ArpEntry]:
    """Assemble ipNetToMediaTable rows into ARP entries.

    The table index is ``ifIndex.a.b.c.d``, so both the interface and the IP
    address come out of the OID itself.
    """
    types: dict[str, int] = {}
    for oid, value in type_rows or []:
        types[oid_suffix(oid, oids.IP_NET_TO_MEDIA_TYPE)] = _as_int(value, 1)

    entries: list[ArpEntry] = []
    for oid, value in phys_rows:
        index = oid_suffix(oid, oids.IP_NET_TO_MEDIA_PHYS_ADDRESS)
        parts = index.split(".")
        if len(parts) < 5:
            continue

        if_index = parts[0]
        ip_address = ".".join(parts[-4:])
        type_name = oids.ARP_TYPE_NAMES.get(types.get(index, 0), "unknown")

        entries.append(
            ArpEntry(
                ip=ip_address,
                mac=octets_to_mac(value),
                interface=if_index,
                type="static" if type_name == "static" else "dynamic",
            )
        )

    return entries


def build_mac_entries(port_rows: list[WalkRow]) -> list[MacEntry]:
    """Assemble dot1dTpFdbTable rows into MAC table entries.

    BRIDGE-MIB carries no VLAN, which needs Q-BRIDGE-MIB, so ``vlan`` is 0 to
    mean "not reported" rather than NetVault's 1, which claimed VLAN 1.
    """
    entries: list[MacEntry] = []
    for oid, value in port_rows:
        mac = oid_tail_to_mac(oid)
        if not mac:
            continue
        entries.append(MacEntry(mac=mac, port=str(value), vlan=0, type="learned"))
    return entries


def build_routes(
    next_hop_rows: list[WalkRow],
    metric_rows: list[WalkRow] | None = None,
    proto_rows: list[WalkRow] | None = None,
) -> list[RouteEntry]:
    """Assemble ipRouteTable rows into routes."""
    metrics: dict[str, int] = {
        oid_suffix(oid, oids.IP_ROUTE_METRIC1): _as_int(value, 0)
        for oid, value in metric_rows or []
    }
    protos: dict[str, int] = {
        oid_suffix(oid, oids.IP_ROUTE_PROTO): _as_int(value, 1)
        for oid, value in proto_rows or []
    }

    routes: list[RouteEntry] = []
    for oid, value in next_hop_rows:
        destination = oid_suffix(oid, oids.IP_ROUTE_NEXT_HOP)
        metric = metrics.get(destination, 0)
        proto_code = protos.get(destination)

        routes.append(
            RouteEntry(
                destination=destination,
                gateway=str(value),
                interface="",
                metric=max(metric, 0),
                protocol=oids.ROUTE_PROTO_NAMES.get(proto_code or 0, "unknown"),
            )
        )

    return routes


# ─── Transport ───


class PySnmpTransport:
    """Real SNMP transport built on pysnmp.

    pysnmp is imported lazily. Its API has changed shape repeatedly across major
    versions, and NetVault was bitten by exactly that when v7 renamed ``getCmd``
    to ``get_cmd``. Keeping the import inside the constructor means the rest of
    this module stays importable and testable regardless.
    """

    def __init__(
        self,
        host: str,
        port: int,
        auth_data: Any,
        timeout: float = 2.0,
        retries: int = 1,
    ) -> None:
        from pysnmp.hlapi.v3arch.asyncio import ContextData, SnmpEngine

        self._host = host
        self._port = port
        self._auth_data = auth_data
        self._timeout = timeout
        self._retries = retries
        self._engine = SnmpEngine()
        self._context = ContextData()
        self._target: Any | None = None

    async def _get_target(self) -> Any:
        if self._target is None:
            from pysnmp.hlapi.v3arch.asyncio import UdpTransportTarget

            # pysnmp 7 exposes `create` as a classmethod taking the address.
            # NetVault's spelling, UdpTransportTarget(addr, ...).create(),
            # raises TypeError here because the address lands on `timeout`.
            self._target = await UdpTransportTarget.create(
                (self._host, self._port),
                timeout=self._timeout,
                retries=self._retries,
            )
        return self._target

    async def get(self, oid: str) -> Any | None:
        from pysnmp.hlapi.v3arch.asyncio import ObjectIdentity, ObjectType, get_cmd

        indication, status, _index, var_binds = await get_cmd(
            self._engine,
            self._auth_data,
            await self._get_target(),
            self._context,
            ObjectType(ObjectIdentity(oid)),
        )

        if indication or status:
            logger.debug(
                "SNMP GET %s on %s failed: %s", oid, self._host, indication or status
            )
            return None

        for var_bind in var_binds:
            return var_bind[1]
        return None

    async def walk(self, base_oid: str) -> list[WalkRow]:
        # bulk_walk_cmd is the async generator. `bulk_cmd`, which NetVault used
        # here, is a coroutine for a single request in pysnmp 7, so iterating it
        # raises "'async for' requires an object with __aiter__". Walks were
        # broken as badly as the interface collection that called them.
        from pysnmp.hlapi.v3arch.asyncio import (
            ObjectIdentity,
            ObjectType,
            bulk_walk_cmd,
        )

        rows: list[WalkRow] = []
        iterator = bulk_walk_cmd(
            self._engine,
            self._auth_data,
            await self._get_target(),
            self._context,
            0,
            25,
            ObjectType(ObjectIdentity(base_oid)),
            lexicographicMode=False,
        )

        async for indication, status, _index, var_binds in iterator:
            if indication or status:
                logger.debug(
                    "SNMP WALK %s on %s stopped: %s",
                    base_oid,
                    self._host,
                    indication or status,
                )
                break
            for var_bind in var_binds:
                rows.append((str(var_bind[0]), var_bind[1]))

        return rows

    async def close(self) -> None:
        """Release the engine's transport dispatcher.

        Without this pysnmp leaves a pending timeout task behind for every
        engine, which accumulates in a long-running server. NetVault's
        ``disconnect`` only flipped a boolean.
        """
        self._target = None
        try:
            self._engine.close_dispatcher()
        except Exception as exc:  # noqa: BLE001 - cleanup must never raise
            logger.debug("Ignoring SNMP dispatcher shutdown error: %s", exc)


def build_auth_data(credentials: dict[str, Any]) -> Any:
    """Build pysnmp auth data for v2c or v3.

    Digest names map to the protocol they actually name. NetVault mapped
    ``sha256`` onto SHA-224.
    """
    from pysnmp.hlapi.v3arch.asyncio import CommunityData, UsmUserData
    from pysnmp.hlapi.v3arch.asyncio import (
        usmAesCfb128Protocol,
        usmAesCfb192Protocol,
        usmAesCfb256Protocol,
        usmDESPrivProtocol,
        usmHMAC192SHA256AuthProtocol,
        usmHMAC384SHA512AuthProtocol,
        usmHMACMD5AuthProtocol,
        usmHMACSHAAuthProtocol,
        usmNoAuthProtocol,
        usmNoPrivProtocol,
    )

    version = str(credentials.get("version", "v2c")).lower()

    if version in {"v1", "v2c", "2c"}:
        return CommunityData(credentials.get("community", "public"))

    if version != "v3":
        raise ConnectorError(f"Unsupported SNMP version: {version}")

    auth_protocols = {
        "md5": usmHMACMD5AuthProtocol,
        "sha": usmHMACSHAAuthProtocol,
        "sha1": usmHMACSHAAuthProtocol,
        "sha256": usmHMAC192SHA256AuthProtocol,
        "sha512": usmHMAC384SHA512AuthProtocol,
        "none": usmNoAuthProtocol,
    }
    priv_protocols = {
        "des": usmDESPrivProtocol,
        "aes": usmAesCfb128Protocol,
        "aes128": usmAesCfb128Protocol,
        "aes192": usmAesCfb192Protocol,
        "aes256": usmAesCfb256Protocol,
        "none": usmNoPrivProtocol,
    }

    auth_name = str(credentials.get("auth_proto", "sha")).lower()
    priv_name = str(credentials.get("priv_proto", "aes")).lower()

    if auth_name not in auth_protocols:
        raise ConnectorError(f"Unsupported SNMPv3 auth protocol: {auth_name}")
    if priv_name not in priv_protocols:
        raise ConnectorError(f"Unsupported SNMPv3 privacy protocol: {priv_name}")

    return UsmUserData(
        credentials.get("username"),
        authKey=credentials.get("auth_key"),
        privKey=credentials.get("priv_key"),
        authProtocol=auth_protocols[auth_name],
        privProtocol=priv_protocols[priv_name],
    )


# ─── Connector ───


class SNMPConnector(BaseConnector):
    """Collects device state over SNMP."""

    def __init__(
        self,
        device_id: str,
        device_ip: str,
        credentials: dict[str, Any],
        *,
        transport: SnmpTransport | None = None,
    ) -> None:
        super().__init__(device_id, device_ip, credentials)

        self.port = int(credentials.get("port", 161))
        self.version = str(credentials.get("version", "v2c")).lower()
        self.timeout = float(credentials.get("timeout", 2))
        self.retries = int(credentials.get("retries", 1))
        self._transport = transport

    def _get_transport(self) -> SnmpTransport:
        if self._transport is None:
            self._transport = PySnmpTransport(
                host=self.device_ip,
                port=self.port,
                auth_data=build_auth_data(self.credentials),
                timeout=self.timeout,
                retries=self.retries,
            )
        return self._transport

    # ─── Lifecycle ───

    async def connect(self) -> bool:
        """SNMP is connectionless; this confirms the agent answers."""
        result = await self.test_connection()
        self._is_connected = result.success
        return result.success

    async def disconnect(self) -> None:
        if self._transport is not None:
            await self._transport.close()
        self._is_connected = False

    async def test_connection(self) -> ConnectionTestResult:
        start = time.perf_counter()
        value = await self._get_transport().get(oids.SYS_DESCR)
        latency_ms = (time.perf_counter() - start) * 1000

        if value is None:
            return ConnectionTestResult(
                success=False,
                latency_ms=latency_ms,
                error_message=(
                    "No SNMP response. The agent may be disabled, the community "
                    "or v3 credentials wrong, or UDP 161 filtered."
                ),
            )
        return ConnectionTestResult(success=True, latency_ms=latency_ms)

    # ─── Collection ───

    async def get_system_info(self) -> dict[str, Any]:
        transport = self._get_transport()

        info: dict[str, Any] = {
            "name": str(await transport.get(oids.SYS_NAME) or ""),
            "descr": str(await transport.get(oids.SYS_DESCR) or ""),
            "uptime": str(await transport.get(oids.SYS_UPTIME) or ""),
            "location": str(await transport.get(oids.SYS_LOCATION) or ""),
            "contact": str(await transport.get(oids.SYS_CONTACT) or ""),
            "vendor": "generic",
        }

        description = info["descr"].lower()

        if "mikrotik" in description or "routeros" in description:
            info["vendor"] = "mikrotik"
            info["os"] = "RouterOS"
            if version := await transport.get(oids.MIKROTIK_ROUTEROS_VERSION):
                info["os_version"] = str(version)
            if model := await transport.get(oids.MIKROTIK_MODEL):
                info["model"] = str(model)

        elif "cisco" in description or " ios " in f" {description} ":
            info["vendor"] = "cisco"
            info["os"] = "IOS"
            if model := await transport.get(oids.CISCO_MODEL):
                info["model"] = str(model)

        return info

    async def get_interfaces(self) -> list[InterfaceInfo]:
        transport = self._get_transport()
        columns = {
            "descr": await transport.walk(oids.IF_DESCR),
            "name": await transport.walk(oids.IF_NAME),
            "oper_status": await transport.walk(oids.IF_OPER_STATUS),
            "speed": await transport.walk(oids.IF_SPEED),
            "high_speed": await transport.walk(oids.IF_HIGH_SPEED),
            "mac": await transport.walk(oids.IF_PHYS_ADDRESS),
            "in_octets": await transport.walk(oids.IF_IN_OCTETS),
            "out_octets": await transport.walk(oids.IF_OUT_OCTETS),
            "in_errors": await transport.walk(oids.IF_IN_ERRORS),
        }
        return build_interfaces(columns)

    async def get_arp_table(self) -> list[ArpEntry]:
        transport = self._get_transport()
        return build_arp_entries(
            await transport.walk(oids.IP_NET_TO_MEDIA_PHYS_ADDRESS),
            await transport.walk(oids.IP_NET_TO_MEDIA_TYPE),
        )

    async def get_mac_table(self) -> list[MacEntry]:
        return build_mac_entries(
            await self._get_transport().walk(oids.DOT1D_TP_FDB_PORT)
        )

    async def get_routes(self) -> list[RouteEntry]:
        transport = self._get_transport()
        return build_routes(
            await transport.walk(oids.IP_ROUTE_NEXT_HOP),
            await transport.walk(oids.IP_ROUTE_METRIC1),
            await transport.walk(oids.IP_ROUTE_PROTO),
        )

    # ─── Audit ───

    async def run_audit(self) -> AuditResult:
        """Report on SNMP exposure and observed interface state.

        Read-only: nothing here writes to the device.
        """
        result = AuditResult(device_name=self.device_ip)

        if self.version in {"v1", "v2c", "2c"}:
            result.checks.append(
                AuditCheck(
                    name="SNMP version",
                    status="warning",
                    message=(
                        f"The device is polled over SNMP{self.version}, which sends "
                        f"community strings and data in cleartext."
                    ),
                    details={
                        "recommendation": "Move to SNMPv3 with authPriv.",
                        "version": self.version,
                    },
                )
            )

            community = str(self.credentials.get("community", "")).lower()
            if community in WEAK_COMMUNITIES:
                result.checks.append(
                    AuditCheck(
                        name="Default community string",
                        status="fail",
                        message=(
                            f"The community string {community!r} is a vendor default "
                            f"and grants read access to anyone who can reach UDP 161."
                        ),
                        details={
                            "recommendation": "Set a unique community, or move to v3."
                        },
                    )
                )
        else:
            no_privacy = str(self.credentials.get("priv_proto", "")).lower() in {
                "",
                "none",
            }
            result.checks.append(
                AuditCheck(
                    name="SNMP version",
                    status="warning" if no_privacy else "pass",
                    message=(
                        "SNMPv3 is in use without privacy; payloads are readable."
                        if no_privacy
                        else "SNMPv3 with privacy is in use."
                    ),
                )
            )

        interfaces = await self.get_interfaces()
        if interfaces:
            down = [item for item in interfaces if item.status == "down"]
            erroring = [item for item in interfaces if item.errors > 0]

            result.checks.append(
                AuditCheck(
                    name="Interfaces",
                    status="warning" if down else "pass",
                    message=(
                        f"{len(interfaces) - len(down)} of {len(interfaces)} "
                        f"interfaces are up."
                    ),
                    details={
                        "total": len(interfaces),
                        "down": [item.name for item in down],
                    },
                )
            )

            if erroring:
                result.checks.append(
                    AuditCheck(
                        name="Interface errors",
                        status="warning",
                        message=(
                            f"{len(erroring)} interface(s) report inbound errors, "
                            f"which usually means cabling or duplex problems."
                        ),
                        details={
                            "interfaces": {item.name: item.errors for item in erroring}
                        },
                    )
                )
        else:
            result.checks.append(
                AuditCheck(
                    name="Interfaces",
                    status="warning",
                    message="The device reported no interfaces over SNMP.",
                )
            )

        static_arp = [
            entry for entry in await self.get_arp_table() if entry.type == "static"
        ]
        if static_arp:
            result.checks.append(
                AuditCheck(
                    name="Static ARP bindings",
                    status="warning",
                    message=(
                        f"{len(static_arp)} static ARP binding(s) found. These are "
                        f"often left over from troubleshooting and can mask changes."
                    ),
                    details={"entries": [entry.ip for entry in static_arp]},
                )
            )

        result.summary = (
            f"{len(result.checks)} checks run against {self.device_ip} over "
            f"SNMP{self.version}."
        )
        return result


register_connector("snmp", SNMPConnector)
