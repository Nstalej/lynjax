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


def test_backend_allows_local_vite_frontend_cors_preflight():
    response = client.options(
        "/api/v1/assessments/connectivity-demo",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_connectivity_demo_returns_structured_safe_assessment_report():
    response = client.post(
        "/api/v1/assessments/connectivity-demo",
        json={
            "hosts": ["target-web", "target-metadata"],
            "checks": ["http", "dns"],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["assessment_id"] == "demo-connectivity-target-web-target-metadata"
    assert payload["created_at"] == "2026-06-13T00:00:00Z"
    assert payload["mode"] == "simulation"
    assert payload["network_access"] == "disabled"
    assert payload["targets"] == ["target-web", "target-metadata"]
    assert payload["checks"] == ["http", "dns"]
    assert payload["overall_status"] == "completed"
    assert payload["risk_level"] == "low"
    assert payload["safety_notice"] == (
        "Demo/local assessment only. No sockets are opened, no external networks are scanned, "
        "and no credentials are used."
    )
    assert payload["evidence_summary"] == {
        "items_collected": 4,
        "collection_mode": "simulated",
        "storage": "response-only",
    }
    assert payload["results"] == [
        {
            "target": "target-web",
            "status": "simulated-pass",
            "checks": [
                {
                    "name": "http",
                    "status": "simulated-pass",
                    "summary": "http check simulated successfully for target-web",
                },
                {
                    "name": "dns",
                    "status": "simulated-pass",
                    "summary": "dns check simulated successfully for target-web",
                },
            ],
        },
        {
            "target": "target-metadata",
            "status": "simulated-pass",
            "checks": [
                {
                    "name": "http",
                    "status": "simulated-pass",
                    "summary": "http check simulated successfully for target-metadata",
                },
                {
                    "name": "dns",
                    "status": "simulated-pass",
                    "summary": "dns check simulated successfully for target-metadata",
                },
            ],
        },
    ]
    assert payload["report_markdown"].startswith("# Lynjax Connectivity Demo Assessment")
    assert "Assessment ID: demo-connectivity-target-web-target-metadata" in payload["report_markdown"]
    assert "Safety Notice" in payload["report_markdown"]
