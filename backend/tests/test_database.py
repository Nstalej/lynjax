"""Tests for the async SQLite layer."""

from __future__ import annotations

import pytest

from lynjax.core.database import MIGRATIONS, Database, DatabaseError


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "test.db")
    await database.connect()
    try:
        yield database
    finally:
        await database.disconnect()


class TestLifecycle:
    async def test_connect_creates_the_file_and_parent_directories(self, tmp_path):
        target = tmp_path / "nested" / "deeper" / "test.db"
        database = Database(target)

        await database.connect()
        try:
            assert target.exists()
        finally:
            await database.disconnect()

    async def test_connect_is_idempotent(self, db):
        await db.connect()

        assert await db.get_schema_version() == MIGRATIONS[-1][0]

    async def test_queries_after_disconnect_raise_a_clear_error(self, tmp_path):
        database = Database(tmp_path / "test.db")
        await database.connect()
        await database.disconnect()

        with pytest.raises(DatabaseError, match="not connected"):
            await database.fetch_all("SELECT 1")

    async def test_works_as_an_async_context_manager(self, tmp_path):
        async with Database(tmp_path / "test.db") as database:
            assert await database.get_schema_version() == MIGRATIONS[-1][0]


class TestMigrations:
    async def test_fresh_database_lands_on_the_latest_version(self, db):
        assert await db.get_schema_version() == MIGRATIONS[-1][0]

    async def test_migrations_are_not_reapplied(self, db):
        await db.execute(
            "INSERT INTO credential_store (name, type, encrypted_data) "
            "VALUES ('keep-me', 'ssh', 'ciphertext')"
        )

        await db.migrate()

        rows = await db.fetch_all("SELECT name FROM credential_store")
        assert [row["name"] for row in rows] == ["keep-me"]

    async def test_migration_versions_are_unique_and_ascending(self):
        versions = [version for version, _ in MIGRATIONS]

        assert versions == sorted(set(versions))

    async def test_reopening_an_existing_database_preserves_data(self, tmp_path):
        path = tmp_path / "persist.db"
        async with Database(path) as first:
            await first.execute(
                "INSERT INTO credential_store (name, type, encrypted_data) "
                "VALUES ('survivor', 'snmp', 'ciphertext')"
            )

        async with Database(path) as second:
            row = await second.fetch_one(
                "SELECT name FROM credential_store WHERE name = 'survivor'"
            )

        assert row is not None
        assert row["name"] == "survivor"


class TestPragmas:
    async def test_foreign_keys_are_enforced(self, db):
        """SQLite ignores foreign keys unless the pragma is set explicitly."""
        row = await db.fetch_one("PRAGMA foreign_keys")

        assert list(row.values())[0] == 1

    async def test_journal_mode_is_wal(self, db):
        row = await db.fetch_one("PRAGMA journal_mode")

        assert list(row.values())[0].lower() == "wal"


class TestQueries:
    async def test_execute_returns_the_inserted_row_id(self, db):
        row_id = await db.execute(
            "INSERT INTO credential_store (name, type, encrypted_data) "
            "VALUES ('a', 'ssh', 'x')"
        )

        assert row_id > 0

    async def test_fetch_one_returns_none_when_nothing_matches(self, db):
        assert (
            await db.fetch_one("SELECT * FROM credential_store WHERE id = 999") is None
        )

    async def test_fetch_all_returns_dictionaries(self, db):
        await db.execute(
            "INSERT INTO credential_store (name, type, encrypted_data) "
            "VALUES ('a', 'ssh', 'x')"
        )

        rows = await db.fetch_all("SELECT name, type FROM credential_store")

        assert rows == [{"name": "a", "type": "ssh"}]

    async def test_parameters_are_bound_not_interpolated(self, db):
        """A bound parameter must never be executed as SQL."""
        hostile = "'; DROP TABLE credential_store; --"

        await db.execute(
            "INSERT INTO credential_store (name, type, encrypted_data) VALUES (?, ?, ?)",
            (hostile, "ssh", "x"),
        )
        rows = await db.fetch_all("SELECT name FROM credential_store")

        assert rows == [{"name": hostile}]

    async def test_execute_many_inserts_every_row(self, db):
        await db.execute_many(
            "INSERT INTO credential_store (name, type, encrypted_data) VALUES (?, ?, ?)",
            [("a", "ssh", "x"), ("b", "snmp", "y"), ("c", "rest", "z")],
        )

        rows = await db.fetch_all("SELECT name FROM credential_store ORDER BY name")

        assert [row["name"] for row in rows] == ["a", "b", "c"]
