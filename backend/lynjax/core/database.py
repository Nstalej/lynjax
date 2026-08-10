"""Async SQLite access and schema migrations.

Ported from the NetVault database layer, with three deliberate changes:

* **No singleton.** NetVault reached for a module-level instance, which forced
  tests to reset private module state between cases. Callers own the instance
  here and pass it explicitly.
* **Migrations are a declared list.** NetVault used a chain of ``if version < n``
  blocks that were easy to get wrong and impossible to enumerate. Each migration
  below is a numbered entry, applied in order inside a transaction.
* **Foreign keys are enforced.** SQLite leaves them off unless asked, so
  NetVault's ``ON DELETE CASCADE`` clauses never actually fired.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("lynjax.database")

#: Ordered schema migrations. Append only; never edit an applied entry.
MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS credential_store (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL UNIQUE,
            type          TEXT NOT NULL,
            encrypted_data TEXT NOT NULL,
            created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at    TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_credential_store_name
            ON credential_store(name);
        """,
    ),
    (
        2,
        """
        -- One host column, not NetVault's parallel `ip` and `ip_address`, which
        -- drifted apart and left callers guessing which one was populated.
        -- The credential link is by name and really points at credential_store;
        -- NetVault's foreign key named a `credentials` table that the vault
        -- never wrote to, and nothing caught it because foreign keys were off.
        CREATE TABLE IF NOT EXISTS devices (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            name               TEXT NOT NULL UNIQUE,
            host               TEXT NOT NULL,
            port               INTEGER,
            connector_type     TEXT NOT NULL,
            device_type        TEXT NOT NULL DEFAULT 'auto',
            credential_name    TEXT,
            description        TEXT,
            is_active          INTEGER NOT NULL DEFAULT 1,
            status             TEXT NOT NULL DEFAULT 'unknown',
            last_seen          TIMESTAMP,
            last_status_change TIMESTAMP,
            created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at         TIMESTAMP,
            FOREIGN KEY (credential_name)
                REFERENCES credential_store(name)
                ON DELETE SET NULL
                ON UPDATE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_devices_host ON devices(host);
        CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(is_active);
        """,
    ),
    (
        3,
        """
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            full_name       TEXT,
            role            TEXT NOT NULL DEFAULT 'viewer',
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """,
    ),
    (
        4,
        """
        -- Audit history. Reports used to live only in the process's memory, so
        -- a restart erased every past run and the Audits screen had nothing to
        -- list. The findings are stored with the run: re-deriving them would
        -- mean touching the client's network again to redraw a past report.
        CREATE TABLE IF NOT EXISTS audits (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id TEXT NOT NULL UNIQUE,
            client        TEXT,
            target        TEXT NOT NULL DEFAULT 'Global Network',
            audit_type    TEXT NOT NULL DEFAULT 'network',
            device_id     INTEGER,
            status        TEXT NOT NULL DEFAULT 'success',
            verdict       TEXT NOT NULL DEFAULT 'pass',
            checks_total  INTEGER NOT NULL DEFAULT 0,
            issues_total  INTEGER NOT NULL DEFAULT 0,
            summary       TEXT,
            payload_json  TEXT NOT NULL,
            locale        TEXT NOT NULL DEFAULT 'es',
            started_at    TIMESTAMP NOT NULL,
            completed_at  TIMESTAMP,
            created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_audits_started ON audits(started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audits_type ON audits(audit_type);

        -- Remote agents. The Windows AD collector is not ported yet, but the
        -- registration and heartbeat surface is what tells an operator whether
        -- one is alive, and the screen is useless without it.
        CREATE TABLE IF NOT EXISTS agents (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id       TEXT NOT NULL UNIQUE,
            name           TEXT NOT NULL,
            host           TEXT NOT NULL,
            agent_type     TEXT NOT NULL DEFAULT 'windows_ad',
            version        TEXT,
            last_heartbeat TIMESTAMP,
            registered_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_agents_agent_id ON agents(agent_id);
        """,
    ),
)


class DatabaseError(RuntimeError):
    """Raised when the database cannot be opened or migrated."""


class Database:
    """A single async SQLite connection with migration support."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    # ─── Lifecycle ───

    async def connect(self) -> None:
        """Open the connection, enforce pragmas, and bring the schema up to date."""
        if self._connection is not None:
            return

        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(
                f"Cannot create the database directory {self.db_path.parent}: {exc}"
            ) from exc

        try:
            self._connection = await aiosqlite.connect(self.db_path)
        except aiosqlite.Error as exc:
            raise DatabaseError(
                f"Cannot open the database {self.db_path}: {exc}"
            ) from exc

        self._connection.row_factory = aiosqlite.Row
        # Without this SQLite silently ignores every foreign key constraint.
        await self._connection.execute("PRAGMA foreign_keys = ON")
        # WAL keeps reads from blocking the polling writes.
        await self._connection.execute("PRAGMA journal_mode = WAL")
        await self._connection.commit()

        await self.migrate()
        logger.info("Database ready at %s", self.db_path)

    async def disconnect(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def __aenter__(self) -> Database:
        await self.connect()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.disconnect()

    @property
    def _conn(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise DatabaseError("Database is not connected. Call connect() first.")
        return self._connection

    # ─── Migrations ───

    async def get_schema_version(self) -> int:
        async with self._conn.execute("PRAGMA user_version") as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def migrate(self) -> int:
        """Apply every pending migration in order. Returns the resulting version.

        ``PRAGMA user_version`` is SQLite's own counter, so the schema version
        cannot drift away from a hand-maintained settings row the way NetVault's
        ``sys_config`` value could.
        """
        current = await self.get_schema_version()

        for version, script in MIGRATIONS:
            if version <= current:
                continue
            logger.info("Applying database migration %s", version)
            try:
                await self._conn.executescript(script)
                # executescript commits implicitly, so set the version after it.
                await self._conn.execute(f"PRAGMA user_version = {version}")
                await self._conn.commit()
            except aiosqlite.Error as exc:
                raise DatabaseError(f"Migration {version} failed: {exc}") from exc
            current = version

        return current

    # ─── Queries ───

    async def execute(self, query: str, parameters: Sequence[Any] = ()) -> int:
        """Run a write statement and return ``lastrowid``."""
        async with self._conn.execute(query, parameters) as cursor:
            await self._conn.commit()
            return cursor.lastrowid or 0

    async def fetch_one(
        self, query: str, parameters: Sequence[Any] = ()
    ) -> dict[str, Any] | None:
        async with self._conn.execute(query, parameters) as cursor:
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def fetch_all(
        self, query: str, parameters: Sequence[Any] = ()
    ) -> list[dict[str, Any]]:
        async with self._conn.execute(query, parameters) as cursor:
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def execute_many(
        self, query: str, parameter_sets: Iterable[Sequence[Any]]
    ) -> None:
        await self._conn.executemany(query, parameter_sets)
        await self._conn.commit()
