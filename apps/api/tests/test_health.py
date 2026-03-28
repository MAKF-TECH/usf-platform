"""Tests for GET /health endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


async def test_health_returns_ok():
    """GET /health → {"status": "ok", "service": "usf-api"}."""
    from usf_api.routers.health import health as health_handler
    from usf_api.config import Settings

    # Build a mock request with a working cache ping
    mock_cache = AsyncMock()
    mock_cache.ping = AsyncMock(return_value=True)

    mock_app_state = MagicMock()
    mock_app_state.cache = mock_cache

    mock_request = MagicMock()
    mock_request.app.state = mock_app_state

    with patch("usf_api.routers.health.settings") as mock_settings:
        mock_settings.service_name = "usf-api"
        result = await health_handler(mock_request)

    assert result["status"] == "ok"
    assert result["service"] == "usf-api"


async def test_health_cache_degraded_when_ping_fails():
    """GET /health → cache=degraded when Valkey is unreachable."""
    from usf_api.routers.health import health as health_handler

    mock_cache = AsyncMock()
    mock_cache.ping = AsyncMock(side_effect=ConnectionError("redis unavailable"))

    mock_app_state = MagicMock()
    mock_app_state.cache = mock_cache

    mock_request = MagicMock()
    mock_request.app.state = mock_app_state

    with patch("usf_api.routers.health.settings") as mock_settings:
        mock_settings.service_name = "usf-api"
        result = await health_handler(mock_request)

    assert result["status"] == "ok"
    assert result["cache"] == "degraded"
