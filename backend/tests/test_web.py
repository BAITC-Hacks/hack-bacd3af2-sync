from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.web import mount_dashboard


def test_dashboard_routes_preserve_api_and_missing_assets(tmp_path):
    (tmp_path / "index.html").write_text("<html>WindAI dashboard</html>", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.log('WindAI')", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    mount_dashboard(app, tmp_path)
    with TestClient(app) as client:
        for route in ("/", "/forecast", "/about"):
            response = client.get(route)
            assert response.status_code == 200
            assert "WindAI dashboard" in response.text
            assert response.headers["cache-control"] == "no-cache"
        assert client.get("/app.js").status_code == 200
        assert client.get("/api/health").json() == {"status": "ok"}
        for route in ("/api/missing", "/missing.js", "/%2e%2e/secret"):
            assert client.get(route).status_code == 404


def test_missing_frontend_build_fails_fast(tmp_path):
    with pytest.raises(RuntimeError, match="Frontend build missing"):
        mount_dashboard(FastAPI(), tmp_path)
