"""Shared fixtures for apps/kg tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_arcadedb_client():
    """Mock ArcadeDB client with all methods as AsyncMock."""
    client = AsyncMock()
    client.get_node = AsyncMock(return_value=None)
    client.upsert_node = AsyncMock(return_value="usf://test/entity/Test/abc123")
    client.vector_search = AsyncMock(return_value=[])
    client.traverse = AsyncMock(return_value=[])
    client.execute_cypher = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_qlever_service():
    """Mock QLever service."""
    service = AsyncMock()
    service.insert_triples = AsyncMock(return_value=None)
    service.query = AsyncMock(return_value={"results": {"bindings": []}})
    return service
