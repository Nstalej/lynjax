"""Tests for the encrypted credential vault.

This module holds real client secrets during field work, so the tests cover the
failure modes that matter operationally: a rotated key, a stale ciphertext, and
the purge that has to leave nothing behind.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.core.database import Database
from app.services.vault import (
    CredentialNotFoundError,
    CredentialVault,
    VaultDecryptionError,
    VaultError,
)

SSH_CREDENTIAL = {
    "username": "operator",
    "password": "s3cr3t-passphrase",
    "port": 22,
    "device_type": "mikrotik",
}


@pytest.fixture
def master_key() -> str:
    return Fernet.generate_key().decode("utf-8")


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "vault.db")
    await database.connect()
    try:
        yield database
    finally:
        await database.disconnect()


@pytest.fixture
def vault(db, master_key) -> CredentialVault:
    return CredentialVault(db, master_key)


class TestKeyHandling:
    def test_a_generated_fernet_key_is_used_directly(self, db, master_key):
        assert CredentialVault(db, master_key) is not None

    def test_an_operator_passphrase_is_accepted(self, db):
        """Humans set memorable passphrases; the vault derives a key from them."""
        assert CredentialVault(db, "correct horse battery staple") is not None

    def test_passphrase_derivation_is_deterministic(self, db):
        """The same passphrase must open the vault after the file is moved."""
        one = CredentialVault(db, "shared passphrase")
        two = CredentialVault(db, "shared passphrase")

        assert two.decrypt(one.encrypt("payload")) == "payload"

    def test_different_passphrases_produce_different_vaults(self, db):
        one = CredentialVault(db, "passphrase one")
        two = CredentialVault(db, "passphrase two")

        with pytest.raises(VaultDecryptionError):
            two.decrypt(one.encrypt("payload"))

    def test_an_empty_key_is_rejected_with_an_actionable_message(self, db):
        with pytest.raises(VaultError, match="LYNJAX_CREDENTIALS_MASTER_KEY"):
            CredentialVault(db, "")


class TestRoundTrip:
    async def test_a_stored_credential_comes_back_intact(self, vault):
        await vault.store("mikrotik-core", "ssh", SSH_CREDENTIAL)

        assert await vault.get("mikrotik-core") == SSH_CREDENTIAL

    async def test_the_record_carries_metadata_alongside_the_payload(self, vault):
        await vault.store("mikrotik-core", "ssh", SSH_CREDENTIAL)

        record = await vault.get_record("mikrotik-core")

        assert record["name"] == "mikrotik-core"
        assert record["type"] == "ssh"
        assert record["data"] == SSH_CREDENTIAL
        assert record["created_at"]

    async def test_nested_payloads_survive_the_round_trip(self, vault):
        payload = {"snmp": {"v3": {"auth": "SHA", "priv": "AES"}}, "retries": [1, 2, 3]}

        await vault.store("complex", "snmp", payload)

        assert await vault.get("complex") == payload


class TestEncryptionAtRest:
    async def test_the_secret_is_not_readable_in_the_database(self, vault, db):
        await vault.store("mikrotik-core", "ssh", SSH_CREDENTIAL)

        row = await db.fetch_one(
            "SELECT encrypted_data FROM credential_store WHERE name = 'mikrotik-core'"
        )

        assert "s3cr3t-passphrase" not in row["encrypted_data"]
        assert "operator" not in row["encrypted_data"]

    async def test_the_same_payload_encrypts_differently_each_time(self, vault):
        first = vault.encrypt("identical")
        second = vault.encrypt("identical")

        assert first != second

    async def test_a_rotated_key_cannot_read_old_data(self, db, master_key):
        original = CredentialVault(db, master_key)
        await original.store("mikrotik-core", "ssh", SSH_CREDENTIAL)

        rotated = CredentialVault(db, Fernet.generate_key().decode("utf-8"))

        with pytest.raises(VaultDecryptionError, match="master key"):
            await rotated.get("mikrotik-core")

    async def test_tampered_ciphertext_is_rejected(self, vault, db):
        await vault.store("mikrotik-core", "ssh", SSH_CREDENTIAL)
        await db.execute(
            "UPDATE credential_store SET encrypted_data = ? WHERE name = ?",
            ("gAAAAABmtampered", "mikrotik-core"),
        )

        with pytest.raises(VaultDecryptionError):
            await vault.get("mikrotik-core")


class TestUpdatesAndDeletes:
    async def test_storing_twice_updates_instead_of_duplicating(self, vault):
        await vault.store("device", "ssh", {"password": "old"})
        await vault.store("device", "ssh", {"password": "new"})

        assert await vault.get("device") == {"password": "new"}
        assert len(await vault.list_metadata()) == 1

    async def test_storing_twice_can_change_the_type(self, vault):
        await vault.store("device", "ssh", {"password": "x"})
        await vault.store("device", "snmp", {"community": "public"})

        record = await vault.get_record("device")

        assert record["type"] == "snmp"

    async def test_delete_removes_the_credential(self, vault):
        await vault.store("device", "ssh", SSH_CREDENTIAL)

        await vault.delete("device")

        assert await vault.exists("device") is False

    async def test_deleting_an_unknown_credential_raises(self, vault):
        with pytest.raises(CredentialNotFoundError):
            await vault.delete("never-existed")


class TestLookupFailures:
    async def test_getting_an_unknown_credential_raises(self, vault):
        with pytest.raises(CredentialNotFoundError, match="ghost"):
            await vault.get("ghost")

    async def test_exists_reports_presence(self, vault):
        await vault.store("present", "ssh", SSH_CREDENTIAL)

        assert await vault.exists("present") is True
        assert await vault.exists("absent") is False


class TestListing:
    async def test_listing_never_exposes_the_payload(self, vault):
        await vault.store("device", "ssh", SSH_CREDENTIAL)

        entries = await vault.list_metadata()

        assert entries[0]["name"] == "device"
        assert "data" not in entries[0]
        assert "encrypted_data" not in entries[0]

    async def test_listing_is_sorted_by_name(self, vault):
        for name in ("zulu", "alpha", "mike"):
            await vault.store(name, "ssh", SSH_CREDENTIAL)

        entries = await vault.list_metadata()

        assert [entry["name"] for entry in entries] == ["alpha", "mike", "zulu"]

    async def test_listing_an_empty_vault_returns_nothing(self, vault):
        assert await vault.list_metadata() == []


class TestPurge:
    async def test_purge_removes_every_credential(self, vault):
        """After an authorised assessment, client secrets must leave the laptop."""
        for name in ("one", "two", "three"):
            await vault.store(name, "ssh", SSH_CREDENTIAL)

        removed = await vault.purge_all()

        assert removed == 3
        assert await vault.list_metadata() == []

    async def test_purging_an_empty_vault_is_safe(self, vault):
        assert await vault.purge_all() == 0
