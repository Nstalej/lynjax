"""Device inventory storage.

Replaces NetVault's ``DeviceManager``, which was a singleton holding three
parallel in-memory caches (``_devices``, ``_connectors``, ``_cache``) that could
disagree with each other and with the database. This is a plain repository: the
database is the single source of truth and callers own the instance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from app.core.database import Database

logger = logging.getLogger("lynjax.devices")

DeviceStatus = Literal["online", "offline", "warning", "unknown"]

#: Default port per connector type, used when a device record omits one.
DEFAULT_PORTS: dict[str, int] = {"ssh": 22, "snmp": 161, "rest": 443}


class DeviceError(RuntimeError):
    """Base class for device inventory failures."""


class DeviceNotFoundError(DeviceError):
    """No device matches the given identifier."""


class DuplicateDeviceError(DeviceError):
    """A device already exists with that name."""


@dataclass(frozen=True)
class Device:
    """One managed device."""

    id: int
    name: str
    host: str
    connector_type: str
    device_type: str = "auto"
    port: int | None = None
    credential_name: str | None = None
    description: str | None = None
    is_active: bool = True
    status: DeviceStatus = "unknown"
    last_seen: str | None = None

    @property
    def effective_port(self) -> int:
        """The configured port, or the default for this connector type."""
        if self.port:
            return self.port
        return DEFAULT_PORTS.get(self.connector_type, 0)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Device:
        return cls(
            id=int(row["id"]),
            name=row["name"],
            host=row["host"],
            connector_type=row["connector_type"],
            device_type=row["device_type"],
            port=row["port"],
            credential_name=row["credential_name"],
            description=row["description"],
            is_active=bool(row["is_active"]),
            status=row["status"],
            last_seen=row["last_seen"],
        )


class DeviceRepository:
    """Reads and writes the device inventory."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(
        self,
        *,
        name: str,
        host: str,
        connector_type: str,
        device_type: str = "auto",
        port: int | None = None,
        credential_name: str | None = None,
        description: str | None = None,
    ) -> Device:
        if await self.exists(name):
            raise DuplicateDeviceError(f"A device named {name!r} already exists")

        await self._db.execute(
            """
            INSERT INTO devices
                (name, host, port, connector_type, device_type,
                 credential_name, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                host,
                port,
                connector_type,
                device_type,
                credential_name,
                description,
            ),
        )
        logger.info("Registered device %r at %s over %s", name, host, connector_type)
        return await self.get_by_name(name)

    async def get(self, device_id: int) -> Device:
        row = await self._db.fetch_one(
            "SELECT * FROM devices WHERE id = ?", (device_id,)
        )
        if row is None:
            raise DeviceNotFoundError(f"No device with id {device_id}")
        return Device.from_row(row)

    async def get_by_name(self, name: str) -> Device:
        row = await self._db.fetch_one("SELECT * FROM devices WHERE name = ?", (name,))
        if row is None:
            raise DeviceNotFoundError(f"No device named {name!r}")
        return Device.from_row(row)

    async def exists(self, name: str) -> bool:
        return (
            await self._db.fetch_one("SELECT 1 FROM devices WHERE name = ?", (name,))
            is not None
        )

    async def list(self, *, active_only: bool = False) -> list[Device]:
        query = "SELECT * FROM devices"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        return [Device.from_row(row) for row in await self._db.fetch_all(query)]

    async def update_status(
        self, device_id: int, status: DeviceStatus, *, seen: bool = False
    ) -> None:
        """Record a new status.

        ``last_status_change`` only moves when the status actually changes, so
        it answers "since when" rather than "when did we last poll".
        """
        current = await self.get(device_id)
        changed = current.status != status

        await self._db.execute(
            f"""
            UPDATE devices
               SET status = ?,
                   updated_at = CURRENT_TIMESTAMP
                   {", last_status_change = CURRENT_TIMESTAMP" if changed else ""}
                   {", last_seen = CURRENT_TIMESTAMP" if seen else ""}
             WHERE id = ?
            """,
            (status, device_id),
        )

        if changed:
            logger.info(
                "Device %r moved from %s to %s", current.name, current.status, status
            )

    async def set_active(self, device_id: int, is_active: bool) -> None:
        await self.get(device_id)
        await self._db.execute(
            "UPDATE devices SET is_active = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (1 if is_active else 0, device_id),
        )

    async def delete(self, device_id: int) -> None:
        await self.get(device_id)
        await self._db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        logger.info("Deleted device %s", device_id)

    async def purge_all(self) -> int:
        """Remove every device. Used to clear a client's data after field work."""
        rows = await self._db.fetch_all("SELECT COUNT(*) AS n FROM devices")
        count = int(rows[0]["n"]) if rows else 0
        await self._db.execute("DELETE FROM devices")
        logger.warning("Purged %s device(s) from the inventory", count)
        return count
