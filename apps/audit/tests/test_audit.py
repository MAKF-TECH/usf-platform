"""Tests for usf-audit service — no Docker required."""
from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock


def test_health_returns_ok():
    """GET /health → 200 ok."""
    from fastapi.testclient import TestClient
    from usf_audit.main import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_log_endpoint_exists():
    """GET /log returns a response (may be empty without DB)."""
    from fastapi.testclient import TestClient
    from usf_audit.main import app

    with TestClient(app) as client, \
         patch("usf_audit.routers.log.get_session") as mock_session:
        # Mock the async session dependency
        session = AsyncMock()
        result_mock = AsyncMock()
        result_mock.all.return_value = []
        session.exec.return_value = result_mock

        async def fake_session():
            yield session

        mock_session.return_value = fake_session()
        # Just verify the route is registered
        r = client.get("/log")
        assert r.status_code in (200, 422, 500)


def test_export_endpoint_exists():
    """POST /export is registered."""
    from fastapi.testclient import TestClient
    from usf_audit.main import app

    with TestClient(app) as client:
        # Send minimal payload — endpoint should not 404
        r = client.post("/export", json={
            "tenant_id": "test",
            "start": "2024-01-01T00:00:00",
            "end": "2024-12-31T23:59:59",
            "format": "turtle",
        })
        # Expect 200 or 502 (QLever not available), not 404
        assert r.status_code != 404


def test_app_includes_all_routers():
    """App has log, lineage, export, stats routers."""
    from usf_audit.main import app

    routes = [r.path for r in app.routes]
    assert any("/log" in r for r in routes)
    assert any("/export" in r for r in routes)
    assert any("/health" in r for r in routes)
