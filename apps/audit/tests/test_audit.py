"""Tests for usf-audit service."""
from __future__ import annotations

def test_health_returns_ok():
    from fastapi.testclient import TestClient
    from usf_audit.main import app
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

def test_app_includes_routers():
    from usf_audit.main import app
    routes = [r.path for r in app.routes]
    assert any("/log" in r for r in routes)
    assert any("/export" in r for r in routes)
    assert any("/health" in r for r in routes)

def test_export_endpoint_not_404():
    from fastapi.testclient import TestClient
    from usf_audit.main import app
    with TestClient(app) as client:
        r = client.post("/export", json={"tenant_id": "test", "start": "2024-01-01T00:00:00", "end": "2024-12-31T23:59:59", "format": "turtle"})
        assert r.status_code != 404
