"""Tests for the discovery, audit, trace and report endpoints.

Weighted towards the policy gate: these are the endpoints that can reach a
client's infrastructure, and a refusal has to hold at the HTTP boundary too.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lynjax.core.config import Settings, get_settings
from lynjax.core.database import Database
from lynjax.core.deps import get_db, get_vault
from lynjax.main import app
from lynjax.services.users import UserRepository
from lynjax.services.vault import CredentialVault

MASTER_KEY = "vLQ5wYAJc6qHhCUW3wRDGxQ0cWQFWpQxNKZbCKzE1yA="
SECRET = "test-secret-key-for-signing-tokens-long-enough-for-hs256"
ADMIN_PASSWORD = "correct-horse-battery"


@pytest.fixture
async def client(tmp_path):
    database = Database(tmp_path / "network.db")
    await database.connect()
    vault = CredentialVault(database, MASTER_KEY)
    await UserRepository(database).create(
        email="admin@lynjax.test", password=ADMIN_PASSWORD, role="admin"
    )

    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_vault] = lambda: vault
    app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=tmp_path, secret_key=SECRET
    )

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@lynjax.test", "password": ADMIN_PASSWORD},
        )
        assert response.status_code == 200, response.text
        test_client.headers.update(
            {"Authorization": f"Bearer {response.json()['access_token']}"}
        )
        yield test_client

    app.dependency_overrides.clear()
    await database.disconnect()


def allow_network(tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=tmp_path,
        secret_key=SECRET,
        network_policy="authorized-targets",
    )


class TestPolicyGate:
    def test_discovery_is_refused_under_the_default_policy(self, client):
        response = client.post(
            "/api/v1/discovery", json={"subnets": ["192.168.1.0/30"]}
        )

        assert response.status_code == 403
        assert "authorized-targets" in response.json()["detail"]

    def test_audit_is_refused_under_the_default_policy(self, client):
        assert client.post("/api/v1/audit", json={}).status_code == 403

    def test_trace_is_refused_under_the_default_policy(self, client):
        assert client.post("/api/v1/trace/10.0.0.50").status_code == 403

    def test_a_refusal_is_never_a_server_error(self, client):
        """A policy decision must not read to the caller as a crash."""
        for response in (
            client.post("/api/v1/discovery", json={"subnets": ["10.0.0.0/30"]}),
            client.post("/api/v1/audit", json={}),
            client.post("/api/v1/trace/10.0.0.1"),
        ):
            assert response.status_code < 500


class TestDiscoveryScopeValidation:
    def test_an_oversized_scope_is_rejected_as_client_error(self, client, tmp_path):
        allow_network(tmp_path)

        response = client.post(
            "/api/v1/discovery", json={"subnets": ["10.0.0.0/8"], "max_hosts": 4096}
        )

        assert response.status_code == 422
        assert "over the limit" in response.json()["detail"]

    def test_public_space_is_rejected_without_an_opt_in(self, client, tmp_path):
        allow_network(tmp_path)

        response = client.post("/api/v1/discovery", json={"subnets": ["8.8.8.0/30"]})

        assert response.status_code == 422
        assert "written authorisation" in response.json()["detail"]

    def test_a_malformed_subnet_is_rejected(self, client, tmp_path):
        allow_network(tmp_path)

        response = client.post("/api/v1/discovery", json={"subnets": ["nonsense"]})

        assert response.status_code == 422

    def test_an_empty_subnet_list_fails_validation(self, client, tmp_path):
        allow_network(tmp_path)

        assert client.post("/api/v1/discovery", json={"subnets": []}).status_code == 422


class TestDiscoveryJobs:
    def test_a_scan_can_be_started_and_polled(self, client, tmp_path):
        """198.51.100.0/30 is RFC 5737 documentation space, routed nowhere."""
        allow_network(tmp_path)

        started = client.post(
            "/api/v1/discovery",
            json={"subnets": ["198.51.100.0/30"], "methods": ["tcp"]},
        )

        assert started.status_code == 202
        job_id = started.json()["job_id"]
        assert client.get(f"/api/v1/discovery/{job_id}").status_code == 200

    def test_jobs_can_be_listed(self, client, tmp_path):
        allow_network(tmp_path)
        client.post(
            "/api/v1/discovery",
            json={"subnets": ["198.51.100.0/32"], "methods": ["tcp"]},
        )

        assert isinstance(client.get("/api/v1/discovery").json(), list)

    def test_an_unknown_job_is_a_404(self, client):
        assert client.get("/api/v1/discovery/no-such-job").status_code == 404

    def test_cancelling_a_finished_job_is_a_conflict_not_a_crash(self, client):
        assert client.delete("/api/v1/discovery/no-such-job").status_code == 409

    def test_the_response_reports_the_scope_and_methods(self, client, tmp_path):
        allow_network(tmp_path)

        body = client.post(
            "/api/v1/discovery",
            json={"subnets": ["198.51.100.0/32"], "methods": ["tcp"]},
        ).json()

        assert body["networks"] == ["198.51.100.0/32"]
        assert body["methods"] == ["tcp"]


class TestAuditAndReports:
    def test_an_audit_with_no_devices_still_returns_a_result(self, client, tmp_path):
        allow_network(tmp_path)

        body = client.post("/api/v1/audit", json={"client": "DGC"}).json()

        assert body["devices_assessed"] == 0
        assert body["verdict"] == "pass"
        assert body["report_url"].startswith("/api/v1/reports/")

    def test_the_report_can_be_downloaded_as_markdown(self, client, tmp_path):
        allow_network(tmp_path)
        assessment_id = client.post(
            "/api/v1/audit", json={"client": "DGC", "locale": "es"}
        ).json()["assessment_id"]

        response = client.get(f"/api/v1/reports/{assessment_id}")

        assert response.status_code == 200
        assert "Informe de auditoría de red" in response.text
        assert "attachment" in response.headers["content-disposition"]

    def test_the_report_can_be_downloaded_as_pdf(self, client, tmp_path):
        pytest.importorskip("reportlab")
        allow_network(tmp_path)
        assessment_id = client.post("/api/v1/audit", json={}).json()["assessment_id"]

        response = client.get(f"/api/v1/reports/{assessment_id}?fmt=pdf")

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")

    def test_the_locale_reaches_the_downloaded_report(self, client, tmp_path):
        allow_network(tmp_path)
        assessment_id = client.post("/api/v1/audit", json={"locale": "en"}).json()[
            "assessment_id"
        ]

        response = client.get(f"/api/v1/reports/{assessment_id}")

        assert "Network audit report" in response.text

    def test_an_unknown_report_explains_that_reports_are_in_memory(self, client):
        response = client.get("/api/v1/reports/never-ran")

        assert response.status_code == 404
        assert "do not survive a restart" in response.json()["detail"]

    def test_an_invalid_format_is_rejected(self, client, tmp_path):
        allow_network(tmp_path)
        assessment_id = client.post("/api/v1/audit", json={}).json()["assessment_id"]

        response = client.get(f"/api/v1/reports/{assessment_id}?fmt=docx")

        assert response.status_code == 422

    def test_an_invalid_locale_is_rejected(self, client, tmp_path):
        allow_network(tmp_path)

        assert client.post("/api/v1/audit", json={"locale": "fr"}).status_code == 422


class TestTrace:
    def test_a_trace_returns_hops_and_a_verdict(self, client, tmp_path):
        allow_network(tmp_path)

        body = client.post("/api/v1/trace/10.0.0.50").json()

        assert body["target"] == "10.0.0.50"
        assert "verdict" in body
        assert isinstance(body["hops"], list)

    def test_an_endpoint_that_cannot_be_located_says_so(self, client, tmp_path):
        """With no devices there is no ARP data, so it must not claim success."""
        allow_network(tmp_path)

        body = client.post("/api/v1/trace/10.0.0.50").json()

        assert body["verdict"] == "warning"
        assert "could not be located" in body["summary"]


class TestFindings:
    def test_findings_are_returned_as_a_list(self, client, tmp_path):
        allow_network(tmp_path)

        response = client.get("/api/v1/audit/findings")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
