"""Shared fixtures for apps/query tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_qlever():
    client = AsyncMock()
    client.query = AsyncMock(return_value={"rows": [], "columns": []})
    client.health = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_arcadedb():
    client = AsyncMock()
    client.cypher = AsyncMock(return_value={"rows": [], "columns": []})
    client.health = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_wren():
    client = AsyncMock()
    client.query = AsyncMock(return_value={"rows": [], "columns": []})
    client.health = AsyncMock(return_value=True)
    return client
