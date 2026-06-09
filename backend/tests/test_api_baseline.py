from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_ok_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_info_reports_beta_backend_metadata():
    response = client.get("/api/v1/info")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Lynjax Backend",
        "version": "0.5.0-beta",
        "environment": "beta-test",
        "network_policy": "simulated-checks-only",
    }


def test_connectivity_demo_returns_safe_simulated_results():
    response = client.post(
        "/api/v1/assessments/connectivity-demo",
        json={
            "hosts": ["target-web", "target-metadata"],
            "checks": ["http", "dns"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "mode": "simulation",
        "network_access": "disabled",
        "results": [
            {
                "host": "target-web",
                "checks": [
                    {"name": "http", "status": "simulated-pass"},
                    {"name": "dns", "status": "simulated-pass"},
                ],
            },
            {
                "host": "target-metadata",
                "checks": [
                    {"name": "http", "status": "simulated-pass"},
                    {"name": "dns", "status": "simulated-pass"},
                ],
            },
        ],
    }
