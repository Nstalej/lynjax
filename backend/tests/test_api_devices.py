"""Tests for the device API, including the network-policy gate.

These drive the app through dependency overrides rather than the lifespan, so
every test gets an isolated database and no filesystem state leaks between them.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lynjax.core.config import Settings, get_settings
from lynjax.core.database import Database
from lynjax.core.deps import get_db, get_vault
from lynjax.main import app
from lynjax.services.connectors.base import (
    AuditCheck,
    AuditResult,
    ConnectionTestResult,
)
from lynjax.services.users import UserRepository
from lynjax.services.vault import CredentialVault

MASTER_KEY = "vLQ5wYAJc6qHhCUW3wRDGxQ0cWQFWpQxNKZbCKzE1yA="
SECRET = "test-secret-key-for-signing-tokens-long-enough-for-hs256"
ADMIN_PASSWORD = "correct-horse-battery"


def authenticate(client: TestClient) -> None:
    """Sign in as the seeded admin and keep the token for every later call.

    Every route requires a token now, so the fixtures carry one rather than each
    test repeating the handshake.
    """
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@lynjax.test", "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    client.headers.update(
        {"Authorization": f"Bearer {response.json()['access_token']}"}
    )


@pytest.fixture
async def wired(tmp_path):
    """An app with an isolated database, vault and simulated-only policy."""
    database = Database(tmp_path / "api.db")
    await database.connect()
    vault = CredentialVault(database, MASTER_KEY)
    settings = Settings(data_dir=tmp_path, secret_key=SECRET)
    await UserRepository(database).create(
        email="admin@lynjax.test", password=ADMIN_PASSWORD, role="admin"
    )

    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_vault] = lambda: vault
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        authenticate(client)
        yield client, database, vault

    app.dependency_overrides.clear()
    await database.disconnect()


@pytest.fixture
def client(wired):
    return wired[0]


def allow_network(tmp_path):
    """Swap in settings that permit real network access."""
    app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=tmp_path,
        secret_key=SECRET,
        network_policy="authorized-targets",
    )


class TestInventory:
    def test_a_device_can_be_created_and_listed(self, client):
        created = client.post(
            "/api/v1/devices",
            json={"name": "core", "host": "10.0.0.1", "connector_type": "ssh"},
        )

        assert created.status_code == 201
        assert created.json()["name"] == "core"
        assert [d["name"] for d in client.get("/api/v1/devices").json()] == ["core"]

    def test_the_default_port_is_filled_in_from_the_connector(self, client):
        response = client.post(
            "/api/v1/devices",
            json={"name": "snmp-sw", "host": "10.0.0.2", "connector_type": "snmp"},
        )

        assert response.json()["port"] == 161

    def test_a_duplicate_name_is_a_conflict(self, client):
        body = {"name": "core", "host": "10.0.0.1", "connector_type": "ssh"}
        client.post("/api/v1/devices", json=body)

        assert client.post("/api/v1/devices", json=body).status_code == 409

    def test_an_unknown_connector_type_is_rejected_by_validation(self, client):
        response = client.post(
            "/api/v1/devices",
            json={"name": "x", "host": "10.0.0.1", "connector_type": "telepathy"},
        )

        assert response.status_code == 422

    def test_an_out_of_range_port_is_rejected(self, client):
        response = client.post(
            "/api/v1/devices",
            json={
                "name": "x",
                "host": "10.0.0.1",
                "connector_type": "ssh",
                "port": 70000,
            },
        )

        assert response.status_code == 422

    def test_a_missing_device_is_a_404(self, client):
        assert client.get("/api/v1/devices/999").status_code == 404

    def test_a_device_can_be_deleted(self, client):
        device_id = client.post(
            "/api/v1/devices",
            json={"name": "core", "host": "10.0.0.1", "connector_type": "ssh"},
        ).json()["id"]

        assert client.delete(f"/api/v1/devices/{device_id}").status_code == 204
        assert client.get(f"/api/v1/devices/{device_id}").status_code == 404


class TestNetworkPolicyGate:
    def test_probing_is_refused_under_the_default_policy(self, wired):
        """The safety switch has to hold at the API boundary too."""
        client, _, vault = wired
        device_id = client.post(
            "/api/v1/devices",
            json={"name": "core", "host": "10.0.0.1", "connector_type": "ssh"},
        ).json()["id"]

        response = client.post(f"/api/v1/devices/{device_id}/check")

        assert response.status_code == 403
        assert "authorized-targets" in response.json()["detail"]

    def test_auditing_is_refused_under_the_default_policy(self, client):
        device_id = client.post(
            "/api/v1/devices",
            json={"name": "core", "host": "10.0.0.1", "connector_type": "ssh"},
        ).json()["id"]

        assert client.post(f"/api/v1/devices/{device_id}/audit").status_code == 403

    def test_the_refusal_is_403_not_500(self, client):
        """A policy decision is not a crash and must not read like one."""
        device_id = client.post(
            "/api/v1/devices",
            json={"name": "core", "host": "10.0.0.1", "connector_type": "ssh"},
        ).json()["id"]

        assert client.post(f"/api/v1/devices/{device_id}/check").status_code != 500


class TestProbing:
    def test_a_device_without_credentials_is_unprocessable(self, wired, tmp_path):
        client, _, _ = wired
        allow_network(tmp_path)
        device_id = client.post(
            "/api/v1/devices",
            json={"name": "core", "host": "10.0.0.1", "connector_type": "ssh"},
        ).json()["id"]

        response = client.post(f"/api/v1/devices/{device_id}/check")

        assert response.status_code == 422
        assert "no credential" in response.json()["detail"]

    def test_a_device_referencing_a_purged_credential_names_it(self, wired, tmp_path):
        client, _, vault = wired
        allow_network(tmp_path)
        device_id = client.post(
            "/api/v1/devices",
            json={"name": "core", "host": "10.0.0.1", "connector_type": "ssh"},
        ).json()["id"]

        response = client.post(f"/api/v1/devices/{device_id}/check")

        assert response.status_code == 422
        assert "core" in response.json()["detail"]


class TestProbingWithAFakeConnector:
    @pytest.fixture(autouse=True)
    def _fake_connector(self, monkeypatch, tmp_path):
        """Replace the built connector so nothing opens a socket."""
        allow_network(tmp_path)

        class FakeConnector:
            def __init__(self, success=True, checks=None):
                self.success = success
                self.checks = checks or []
                self.disconnected = False

            async def test_connection(self):
                return ConnectionTestResult(
                    success=self.success,
                    latency_ms=12.345,
                    error_message=None if self.success else "no route to host",
                )

            async def connect(self):
                return True

            async def run_audit(self):
                return AuditResult(
                    device_name="fake", checks=self.checks, summary="fake audit"
                )

            async def disconnect(self):
                self.disconnected = True

        self.FakeConnector = FakeConnector
        self.instance = FakeConnector()

        async def fake_build(device, vault, settings):
            return self.instance

        monkeypatch.setattr("lynjax.api.routes.devices.build_connector", fake_build)

    def _create(self, client):
        return client.post(
            "/api/v1/devices",
            json={"name": "core", "host": "10.0.0.1", "connector_type": "ssh"},
        ).json()["id"]

    def test_a_reachable_device_reports_latency(self, client):
        device_id = self._create(client)

        body = client.post(f"/api/v1/devices/{device_id}/check").json()

        assert body["reachable"] is True
        assert body["latency_ms"] == 12.35

    def test_a_successful_probe_marks_the_device_online(self, client):
        device_id = self._create(client)

        client.post(f"/api/v1/devices/{device_id}/check")

        assert client.get(f"/api/v1/devices/{device_id}").json()["status"] == "online"

    def test_a_failed_probe_marks_the_device_offline_and_carries_the_reason(
        self, client
    ):
        self.instance.success = False
        device_id = self._create(client)

        body = client.post(f"/api/v1/devices/{device_id}/check").json()

        assert body["reachable"] is False
        assert body["error"] == "no route to host"
        assert client.get(f"/api/v1/devices/{device_id}").json()["status"] == "offline"

    def test_the_connector_is_always_released(self, client):
        device_id = self._create(client)

        client.post(f"/api/v1/devices/{device_id}/check")

        assert self.instance.disconnected is True

    def test_an_audit_returns_its_checks(self, client):
        self.instance.checks = [
            AuditCheck(name="Interfaces", status="warning", message="1 port down")
        ]
        device_id = self._create(client)

        body = client.post(f"/api/v1/devices/{device_id}/audit").json()

        assert body["overall_status"] == "warning"
        assert body["checks"][0]["name"] == "Interfaces"

    def test_a_clean_audit_marks_the_device_online(self, client):
        self.instance.checks = [
            AuditCheck(name="Interfaces", status="pass", message="all up")
        ]
        device_id = self._create(client)

        client.post(f"/api/v1/devices/{device_id}/audit")

        assert client.get(f"/api/v1/devices/{device_id}").json()["status"] == "online"

    def test_an_audit_with_findings_marks_the_device_warning(self, client):
        self.instance.checks = [
            AuditCheck(name="Interfaces", status="fail", message="core port down")
        ]
        device_id = self._create(client)

        client.post(f"/api/v1/devices/{device_id}/audit")

        assert client.get(f"/api/v1/devices/{device_id}").json()["status"] == "warning"

    def test_the_audit_timestamp_is_returned(self, client):
        device_id = self._create(client)

        body = client.post(f"/api/v1/devices/{device_id}/audit").json()

        assert body["collected_at"]
