from fastapi.testclient import TestClient

from lynjax.main import app

client = TestClient(app)


def test_health_reports_ok_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_info_reports_backend_metadata():
    response = client.get("/api/v1/info")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Lynjax",
        "version": "0.6.0-dev",
        "environment": "development",
        "network_policy": "simulated-checks-only",
    }


def test_the_demo_assessment_endpoint_is_gone():
    """It returned simulated-pass data and was a second, fake way to run an
    assessment. Removed once the real one existed; pinned so it stays removed."""
    response = client.post("/api/v1/assessments/connectivity-demo", json={})

    assert response.status_code in (404, 405)
