"""Shared fixtures for usf-mcp tests."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_usf_api_client():
    client = AsyncMock()
    client.list_metrics.return_value = {
        "data": {"metrics": [{"name": "total_exposure", "description": "Total exposure"}]}
    }
    client.query_metric.return_value = {
        "data": {"total_rows": 10, "rows": [{"value": 100}]}
    }
    client.explain_metric.return_value = {
        "data": {"name": "total_exposure", "sql_template": "SELECT SUM(amount) FROM tx"}
    }
    client.search_entities.return_value = {
        "data": {"entities": [{"iri": "urn:bank:1", "name": "Deutsche Bank"}]}
    }
    client.get_entity.return_value = {
        "data": {"iri": "urn:bank:1", "name": "Deutsche Bank"}
    }
    with patch("usf_mcp.tools.metrics.get_client", return_value=client), \
         patch("usf_mcp.tools.entities.get_client", return_value=client), \
         patch("usf_mcp.tools.contexts.get_client", return_value=client):
        yield client
