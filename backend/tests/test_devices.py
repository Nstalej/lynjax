"""Tests for the device inventory and the connector factory."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.database import Database
from app.services.connector_factory import (
    ConnectorNotAvailableError,
    MissingCredentialError,
    NetworkAccessDenied,
    assert_network_allowed,
    build_connector,
)
from app.services.devices import (
    Device,
    DeviceNotFoundError,
    DeviceRepository,
    DuplicateDeviceError,
)
from app.services.vault import CredentialVault

MASTER_KEY = "vLQ5wYAJc6qHhCUW3wRDGxQ0cWQFWpQxNKZbCKzE1yA="


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "devices.db")
    await database.connect()
    try:
        yield database
    finally:
        await database.disconnect()


@pytest.fixture
def repo(db) -> DeviceRepository:
    return DeviceRepository(db)


@pytest.fixture
def vault(db) -> CredentialVault:
    return CredentialVault(db, MASTER_KEY)


@pytest.fixture
def open_settings(tmp_path) -> Settings:
    """Settings with real network access deliberately enabled."""
    return Settings(data_dir=tmp_path, network_policy="authorized-targets")


class TestCreate:
    async def test_a_created_device_can_be_read_back(self, repo):
        created = await repo.create(
            name="core-switch", host="10.0.0.1", connector_type="ssh"
        )

        assert (await repo.get(created.id)).name == "core-switch"

    async def test_duplicate_names_are_rejected(self, repo):
        await repo.create(name="core", host="10.0.0.1", connector_type="ssh")

        with pytest.raises(DuplicateDeviceError):
            await repo.create(name="core", host="10.0.0.2", connector_type="snmp")

    async def test_a_missing_device_raises(self, repo):
        with pytest.raises(DeviceNotFoundError):
            await repo.get(999)

    async def test_new_devices_start_unknown_and_active(self, repo):
        device = await repo.create(name="core", host="10.0.0.1", connector_type="ssh")

        assert device.status == "unknown"
        assert device.is_active is True


class TestPorts:
    @pytest.mark.parametrize(
        ("connector_type", "expected"), [("ssh", 22), ("snmp", 161), ("rest", 443)]
    )
    async def test_the_default_port_matches_the_connector(
        self, repo, connector_type, expected
    ):
        device = await repo.create(
            name=f"dev-{connector_type}", host="10.0.0.1", connector_type=connector_type
        )

        assert device.effective_port == expected

    async def test_an_explicit_port_wins(self, repo):
        device = await repo.create(
            name="core", host="10.0.0.1", connector_type="ssh", port=2222
        )

        assert device.effective_port == 2222


class TestStatus:
    async def test_status_is_persisted(self, repo):
        device = await repo.create(name="core", host="10.0.0.1", connector_type="ssh")

        await repo.update_status(device.id, "online")

        assert (await repo.get(device.id)).status == "online"

    async def test_last_seen_only_moves_when_asked(self, repo, db):
        device = await repo.create(name="core", host="10.0.0.1", connector_type="ssh")

        await repo.update_status(device.id, "offline")
        row = await db.fetch_one(
            "SELECT last_seen FROM devices WHERE id = ?", (device.id,)
        )

        assert row["last_seen"] is None

    async def test_last_status_change_records_a_transition(self, repo, db):
        device = await repo.create(name="core", host="10.0.0.1", connector_type="ssh")

        await repo.update_status(device.id, "online")
        row = await db.fetch_one(
            "SELECT last_status_change FROM devices WHERE id = ?", (device.id,)
        )

        assert row["last_status_change"] is not None

    async def test_repeating_the_same_status_is_not_a_transition(self, repo, db):
        """It answers "offline since when", not "when did we last poll"."""
        device = await repo.create(name="core", host="10.0.0.1", connector_type="ssh")
        await repo.update_status(device.id, "online")
        first = (
            await db.fetch_one(
                "SELECT last_status_change FROM devices WHERE id = ?", (device.id,)
            )
        )["last_status_change"]

        await repo.update_status(device.id, "online")
        second = (
            await db.fetch_one(
                "SELECT last_status_change FROM devices WHERE id = ?", (device.id,)
            )
        )["last_status_change"]

        assert first == second


class TestListing:
    async def test_listing_is_sorted_by_name(self, repo):
        for name in ("zulu", "alpha", "mike"):
            await repo.create(name=name, host="10.0.0.1", connector_type="ssh")

        assert [d.name for d in await repo.list()] == ["alpha", "mike", "zulu"]

    async def test_inactive_devices_can_be_excluded(self, repo):
        active = await repo.create(name="on", host="10.0.0.1", connector_type="ssh")
        disabled = await repo.create(name="off", host="10.0.0.2", connector_type="ssh")
        await repo.set_active(disabled.id, False)

        listed = await repo.list(active_only=True)

        assert [d.id for d in listed] == [active.id]


class TestDeletion:
    async def test_delete_removes_the_device(self, repo):
        device = await repo.create(name="core", host="10.0.0.1", connector_type="ssh")

        await repo.delete(device.id)

        with pytest.raises(DeviceNotFoundError):
            await repo.get(device.id)

    async def test_deleting_an_unknown_device_raises(self, repo):
        with pytest.raises(DeviceNotFoundError):
            await repo.delete(999)

    async def test_purge_clears_the_inventory(self, repo):
        for name in ("a", "b", "c"):
            await repo.create(name=name, host="10.0.0.1", connector_type="ssh")

        assert await repo.purge_all() == 3
        assert await repo.list() == []


class TestCredentialLink:
    async def test_deleting_a_credential_unlinks_it_rather_than_orphaning(
        self, repo, vault
    ):
        """Foreign keys are enforced now; NetVault had them silently off."""
        await vault.store("switch-ssh", "ssh", {"username": "op", "password": "x"})
        device = await repo.create(
            name="core",
            host="10.0.0.1",
            connector_type="ssh",
            credential_name="switch-ssh",
        )

        await vault.delete("switch-ssh")

        assert (await repo.get(device.id)).credential_name is None

    async def test_a_device_cannot_reference_a_credential_that_does_not_exist(
        self, repo
    ):
        with pytest.raises(Exception):
            await repo.create(
                name="core",
                host="10.0.0.1",
                connector_type="ssh",
                credential_name="never-stored",
            )


class TestNetworkPolicyGate:
    def test_the_default_policy_blocks_real_network_access(self, tmp_path):
        """The safety switch has to be on by default, or it is decoration."""
        with pytest.raises(NetworkAccessDenied, match="authorized-targets"):
            assert_network_allowed(Settings(data_dir=tmp_path))

    def test_an_explicit_opt_in_allows_access(self, open_settings):
        assert_network_allowed(open_settings) is None

    async def test_the_factory_refuses_to_build_under_the_default_policy(
        self, repo, vault, tmp_path
    ):
        await vault.store("cred", "ssh", {"username": "op", "password": "x"})
        device = await repo.create(
            name="core",
            host="10.0.0.1",
            connector_type="ssh",
            credential_name="cred",
        )

        with pytest.raises(NetworkAccessDenied):
            await build_connector(device, vault, Settings(data_dir=tmp_path))


class TestConnectorFactory:
    async def test_it_builds_an_ssh_connector_with_vault_credentials(
        self, repo, vault, open_settings
    ):
        await vault.store(
            "switch-ssh", "ssh", {"username": "operator", "password": "s3cret"}
        )
        device = await repo.create(
            name="core",
            host="10.0.0.1",
            connector_type="ssh",
            device_type="mikrotik",
            credential_name="switch-ssh",
        )

        connector = await build_connector(device, vault, open_settings)

        assert connector.device_ip == "10.0.0.1"
        assert connector.username == "operator"
        assert connector.device_type == "mikrotik"

    async def test_it_builds_an_snmp_connector(self, repo, vault, open_settings):
        await vault.store("switch-snmp", "snmp", {"version": "v2c", "community": "s3c"})
        device = await repo.create(
            name="core",
            host="10.0.0.2",
            connector_type="snmp",
            credential_name="switch-snmp",
        )

        connector = await build_connector(device, vault, open_settings)

        assert connector.port == 161

    async def test_the_device_port_reaches_the_connector(
        self, repo, vault, open_settings
    ):
        await vault.store("cred", "ssh", {"username": "op", "password": "x"})
        device = await repo.create(
            name="core",
            host="10.0.0.1",
            connector_type="ssh",
            port=2222,
            credential_name="cred",
        )

        connector = await build_connector(device, vault, open_settings)

        assert connector.port == 2222

    async def test_an_unknown_connector_type_is_reported_clearly(
        self, repo, vault, open_settings
    ):
        await vault.store("cred", "x", {"username": "op"})
        device = Device(
            id=1,
            name="core",
            host="10.0.0.1",
            connector_type="carrier-pigeon",
            credential_name="cred",
        )

        with pytest.raises(ConnectorNotAvailableError, match="carrier-pigeon"):
            await build_connector(device, vault, open_settings)

    async def test_a_missing_credential_is_reported_by_name(
        self, repo, vault, open_settings
    ):
        device = Device(
            id=1,
            name="core",
            host="10.0.0.1",
            connector_type="ssh",
            credential_name="was-purged",
        )

        with pytest.raises(MissingCredentialError, match="was-purged"):
            await build_connector(device, vault, open_settings)

    async def test_an_ssh_device_without_any_credential_is_refused(
        self, repo, vault, open_settings
    ):
        device = await repo.create(name="core", host="10.0.0.1", connector_type="ssh")

        with pytest.raises(MissingCredentialError, match="no credential"):
            await build_connector(device, vault, open_settings)
