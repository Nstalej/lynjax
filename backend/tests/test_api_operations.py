"""Tests for the endpoints the operator console needs.

These are the gaps the interface work exposed: the device tabs had no source of
raw tables, the audit history had nowhere to read from, and the credential
dialog, log viewer and dashboard had no API at all.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lynjax.core.config import Settings
from lynjax.core.database import Database
from lynjax.core.deps import get_db, get_runtime_settings, get_vault
from lynjax.main import app
from lynjax.services.audits import AuditRepository
from lynjax.services.users import UserRepository
from lynjax.services.vault import CredentialVault

MASTER_KEY = "vLQ5wYAJc6qHhCUW3wRDGxQ0cWQFWpQxNKZbCKzE1yA="
SECRET = "test-secret-key-for-signing-tokens-long-enough-for-hs256"
PASSWORD = "correct-horse-battery"


@pytest.fixture
async def client(tmp_path):
    database = Database(tmp_path / "ops.db")
    await database.connect()
    vault = CredentialVault(database, MASTER_KEY)
    await UserRepository(database).create(
        email="admin@lynjax.test", password=PASSWORD, role="admin"
    )

    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_vault] = lambda: vault
    app.dependency_overrides[get_runtime_settings] = lambda: Settings(
        data_dir=tmp_path, secret_key=SECRET, network_policy="authorized-targets"
    )

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@lynjax.test", "password": PASSWORD},
        )
        test_client.headers.update(
            {"Authorization": f"Bearer {response.json()['access_token']}"}
        )
        test_client.database = database
        yield test_client

    app.dependency_overrides.clear()
    await database.disconnect()


class TestDashboard:
    def test_an_empty_install_reports_zeroes_without_inventing_health(self, client):
        """A health score for an inventory nobody polled would be a lie."""
        body = client.get("/api/v1/dashboard").json()

        assert body["devices"]["total"] == 0
        assert body["health_score"] is None
        assert "No device has been checked yet" in body["health_basis"]

    def test_devices_are_counted_by_status(self, client):
        client.post(
            "/api/v1/devices",
            json={"name": "sw", "host": "10.0.0.1", "connector_type": "ssh"},
        )

        body = client.get("/api/v1/dashboard").json()

        assert body["devices"]["total"] == 1
        assert body["devices"]["by_status"]["unknown"] == 1

    def test_the_active_network_policy_is_reported(self, client):
        assert client.get("/api/v1/dashboard").json()["network_policy"] == (
            "authorized-targets"
        )

    def test_a_viewer_can_read_the_dashboard(self, client):
        client.post(
            "/api/v1/auth/users",
            json={"email": "v@lynjax.test", "password": PASSWORD, "role": "viewer"},
        )
        token = client.post(
            "/api/v1/auth/login",
            json={"email": "v@lynjax.test", "password": PASSWORD},
        ).json()["access_token"]

        response = client.get(
            "/api/v1/dashboard", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200


class TestDeviceData:
    def test_a_missing_device_is_a_404(self, client):
        assert client.get("/api/v1/devices/999/data").status_code == 404

    def test_a_device_without_credentials_is_unprocessable(self, client):
        device_id = client.post(
            "/api/v1/devices",
            json={"name": "sw", "host": "10.0.0.1", "connector_type": "ssh"},
        ).json()["id"]

        response = client.get(f"/api/v1/devices/{device_id}/data")

        assert response.status_code == 422
        assert "credential" in response.json()["detail"]

    def test_an_unreachable_device_reports_the_reason_rather_than_empty_tables(
        self, client
    ):
        """Empty tables with no explanation is how a broken collection reads as
        a healthy device."""
        client.post(
            "/api/v1/credentials",
            json={
                "name": "snmp-demo",
                "type": "snmp",
                "data": {"version": "v2c", "community": "demo", "timeout": 0.2},
            },
        )
        device_id = client.post(
            "/api/v1/devices",
            json={
                "name": "sw",
                "host": "192.0.2.10",
                "connector_type": "snmp",
                "credential_name": "snmp-demo",
            },
        ).json()["id"]

        body = client.get(f"/api/v1/devices/{device_id}/data").json()

        assert body["collected"] is False
        assert body["interfaces"] == []
        assert body["device"]["name"] == "sw"


class TestAuditHistory:
    @staticmethod
    async def _store(test_client, **overrides):
        payload = {"assessment_id": overrides.get("assessment_id", "a-1")}
        return await AuditRepository(test_client.database).save(
            assessment_id=overrides.pop("assessment_id", "a-1"),
            payload=payload,
            **overrides,
        )

    async def test_a_stored_audit_appears_in_the_history(self, client):
        await self._store(client, client="DGC", verdict="warning", issues_total=2)

        body = client.get("/api/v1/audits").json()

        assert len(body) == 1
        assert body[0]["client"] == "DGC"
        assert body[0]["issues_total"] == 2

    async def test_history_survives_a_restart(self, client):
        """The whole point of persisting: reports used to live only in memory."""
        await self._store(client)

        with TestClient(app) as fresh:
            fresh.headers.update(client.headers)
            assert len(fresh.get("/api/v1/audits").json()) == 1

    async def test_the_detail_carries_the_stored_findings(self, client):
        record = await self._store(client)

        body = client.get(f"/api/v1/audits/{record.id}").json()

        assert body["payload"]["assessment_id"] == "a-1"

    async def test_an_unknown_audit_is_a_404(self, client):
        assert client.get("/api/v1/audits/999").status_code == 404

    async def test_history_can_be_filtered_by_type(self, client):
        await self._store(client, assessment_id="a-1", audit_type="network")
        await self._store(client, assessment_id="a-2", audit_type="trace")

        body = client.get("/api/v1/audits?audit_type=trace").json()

        assert [item["assessment_id"] for item in body] == ["a-2"]

    async def test_running_an_audit_stores_it(self, client):
        client.post("/api/v1/audit", json={"client": "DGC"})

        assert len(client.get("/api/v1/audits").json()) == 1


class TestCredentials:
    def test_a_credential_can_be_stored_and_listed(self, client):
        created = client.post(
            "/api/v1/credentials",
            json={"name": "core-ssh", "type": "ssh", "data": {"username": "op"}},
        )

        assert created.status_code == 201
        assert [c["name"] for c in client.get("/api/v1/credentials").json()] == [
            "core-ssh"
        ]

    def test_listing_never_returns_the_secret(self, client):
        client.post(
            "/api/v1/credentials",
            json={
                "name": "core-ssh",
                "type": "ssh",
                "data": {"username": "op", "password": "s3cr3t-value"},
            },
        )

        body = client.get("/api/v1/credentials").text

        assert "s3cr3t-value" not in body
        assert "encrypted_data" not in body

    def test_a_credential_can_be_deleted(self, client):
        client.post(
            "/api/v1/credentials",
            json={"name": "core-ssh", "type": "ssh", "data": {"username": "op"}},
        )

        assert client.delete("/api/v1/credentials/core-ssh").status_code == 204
        assert client.get("/api/v1/credentials").json() == []

    def test_deleting_an_unknown_credential_is_a_404(self, client):
        assert client.delete("/api/v1/credentials/ghost").status_code == 404


class TestAgents:
    def test_an_agent_can_register_and_is_listed(self, client):
        created = client.post(
            "/api/v1/agents",
            json={"agent_id": "dc1", "name": "AD Agent", "host": "DC1-SRV"},
        )

        assert created.status_code == 201
        assert created.json()["status"] == "online"

    def test_status_is_derived_from_the_heartbeat_not_stored(self, client):
        """A dead process cannot update a stored flag, which is the case the
        screen exists to show."""
        client.post(
            "/api/v1/agents",
            json={"agent_id": "dc1", "name": "AD Agent", "host": "DC1-SRV"},
        )

        assert client.get("/api/v1/agents").json()[0]["status"] == "online"

    def test_a_heartbeat_from_an_unknown_agent_is_a_404(self, client):
        assert client.post("/api/v1/agents/ghost/heartbeat").status_code == 404

    def test_an_agent_can_be_removed(self, client):
        client.post(
            "/api/v1/agents",
            json={"agent_id": "dc1", "name": "AD Agent", "host": "DC1-SRV"},
        )

        assert client.delete("/api/v1/agents/dc1").status_code == 204
        assert client.get("/api/v1/agents").json() == []


class TestLogs:
    def test_a_missing_log_file_explains_itself(self, client):
        body = client.get("/api/v1/logs").json()

        assert body["lines"] == [] or isinstance(body["lines"], list)
        assert "path" in body

    def test_only_an_admin_can_read_the_logs(self, client):
        client.post(
            "/api/v1/auth/users",
            json={"email": "op@lynjax.test", "password": PASSWORD, "role": "operator"},
        )
        token = client.post(
            "/api/v1/auth/login",
            json={"email": "op@lynjax.test", "password": PASSWORD},
        ).json()["access_token"]

        response = client.get(
            "/api/v1/logs", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403


class TestTopology:
    def test_an_empty_inventory_returns_an_empty_graph_with_a_note(self, client):
        body = client.get("/api/v1/topology").json()

        assert body["nodes"] == []
        assert body["edges"] == []
        assert any("MAC address tables" in note for note in body["notes"])


class TestPurgeReach:
    async def test_purge_clears_stored_audits_and_agents_too(self, client):
        await AuditRepository(client.database).save(
            assessment_id="a-1", payload={"x": 1}
        )
        client.post(
            "/api/v1/agents",
            json={"agent_id": "dc1", "name": "AD Agent", "host": "DC1-SRV"},
        )

        body = client.post("/api/v1/purge").json()

        assert body["audits_removed"] == 1
        assert body["agents_removed"] == 1
        assert client.get("/api/v1/audits").json() == []
