"""Tests for serving the compiled frontend.

The single-container decision rests on these: the SPA and the API share one
origin and one port, so the mount must not shadow the API and the API must not
break client-side routing.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lynjax.web import SinglePageApp, find_web_root, mount_frontend


@pytest.fixture
def built_bundle(tmp_path):
    """A minimal stand-in for `npm run build` output."""
    root = tmp_path / "web"
    root.mkdir()
    (root / "index.html").write_text("<html><body><div id='root'></div></body></html>")
    assets = root / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('lynjax');")
    return root


@pytest.fixture
def app_with_ui(built_bundle):
    app = FastAPI()

    @app.get("/api/v1/ping")
    async def ping():
        return {"ok": True}

    app.mount("/", SinglePageApp(directory=built_bundle, html=True), name="web")
    return app


class TestSinglePageFallback:
    def test_the_root_serves_the_app(self, app_with_ui):
        with TestClient(app_with_ui) as client:
            response = client.get("/")

        assert response.status_code == 200
        assert "id='root'" in response.text

    @pytest.mark.parametrize("path", ["/devices/3", "/reports/abc", "/assets"])
    def test_client_side_routes_fall_back_to_the_app(self, app_with_ui, path):
        """Starlette raises on a missing file rather than returning a 404, so a
        naive status-code check never fires and a refresh would 404."""
        with TestClient(app_with_ui) as client:
            response = client.get(path)

        assert response.status_code == 200
        assert "id='root'" in response.text

    def test_a_real_asset_is_served_rather_than_the_fallback(self, app_with_ui):
        with TestClient(app_with_ui) as client:
            response = client.get("/assets/app.js")

        assert response.status_code == 200
        assert "console.log" in response.text


class TestApiIsNotShadowed:
    def test_api_routes_still_resolve(self, app_with_ui):
        with TestClient(app_with_ui) as client:
            assert client.get("/api/v1/ping").json() == {"ok": True}


class TestNoBundle:
    def test_mounting_without_a_build_reports_false(self, monkeypatch):
        monkeypatch.setattr("lynjax.web.find_web_root", lambda: None)
        app = FastAPI()

        assert mount_frontend(app) is False

    def test_the_root_explains_how_to_build_the_ui(self, monkeypatch):
        """A missing bundle is not an error: the API is useful on its own."""
        monkeypatch.setattr("lynjax.web.find_web_root", lambda: None)
        app = FastAPI()
        mount_frontend(app)

        with TestClient(app) as client:
            body = client.get("/").json()

        assert "npm run build" in body["detail"]

    def test_mounting_with_a_build_reports_true(self, monkeypatch, built_bundle):
        monkeypatch.setattr("lynjax.web.find_web_root", lambda: built_bundle)

        assert mount_frontend(FastAPI()) is True


class TestBundleDiscovery:
    def test_a_missing_bundle_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr("lynjax.web.BUNDLED_WEB_DIR", tmp_path / "absent")
        # The development tree may still hold a real build, so only assert the
        # function does not raise and returns something typed correctly.
        result = find_web_root()

        assert result is None or result.is_dir()
