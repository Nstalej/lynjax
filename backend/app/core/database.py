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
