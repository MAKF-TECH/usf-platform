"""Tests for usf-mcp tools — no Docker required."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_list_metrics_calls_api(mock_usf_api_client):
    """usf_list_metrics calls usf-api /metrics endpoint."""
    from usf_mcp.tools.metrics import list_metrics

    result = await list_metrics(context="risk")
    mock_usf_api_client.list_metrics.assert_called_once_with(context="risk")
    assert isinstance(result, list)
    assert result[0]["name"] == "total_exposure"


@pytest.mark.asyncio
async def test_list_metrics_no_context(mock_usf_api_client):
    """usf_list_metrics without context lists all."""
    from usf_mcp.tools.metrics import list_metrics

    await list_metrics()
    mock_usf_api_client.list_metrics.assert_called_once_with(context=None)


@pytest.mark.asyncio
async def test_query_metric_calls_client(mock_usf_api_client):
    """usf_query_metric passes params to client."""
    from usf_mcp.tools.metrics import query_metric

    with patch("usf_mcp.tools.metrics.validate_metric_params", return_value=(True, None)):
        result = await query_metric(
            metric="total_exposure",
            dimensions=["region"],
            filters={"currency": "EUR"},
            context="risk",
        )
    mock_usf_api_client.query_metric.assert_called_once()
    assert "data" in result


@pytest.mark.asyncio
async def test_search_entities_returns_list(mock_usf_api_client):
    """usf_search_entities returns list of entities."""
    from usf_mcp.tools.entities import search_entities

    result = await search_entities(query="Deutsche Bank")
    assert isinstance(result, list)
    assert result[0]["name"] == "Deutsche Bank"
    mock_usf_api_client.search_entities.assert_called_once()


@pytest.mark.asyncio
async def test_explain_metric(mock_usf_api_client):
    """explain_metric returns definition with sql_template."""
    from usf_mcp.tools.metrics import explain_metric

    result = await explain_metric(metric="total_exposure")
    assert "data" in result
    mock_usf_api_client.explain_metric.assert_called_once()
