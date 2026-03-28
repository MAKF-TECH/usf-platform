"""Tests for NamedGraphManager — verifies SPARQL generation and response parsing."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from usf_rdf.graph import NamedGraphManager


@pytest.fixture
def mock_sparql_client():
    client = AsyncMock()
    client.update = AsyncMock(return_value=None)
    client.query = AsyncMock(return_value={"results": {"bindings": []}})
    client.ask = AsyncMock(return_value=False)
    client.bindings = MagicMock(return_value=[])
    return client


async def test_create_named_graph_builds_sparql(mock_sparql_client):
    """Verify SPARQL UPDATE CLEAR is formed correctly for graph creation."""
    manager = NamedGraphManager(mock_sparql_client)
    graph_uri = "usf://acme/context/finance/v1"

    await manager.create_or_clear(graph_uri)

    mock_sparql_client.update.assert_called_once()
    call_args = mock_sparql_client.update.call_args[0][0]
    assert "CLEAR GRAPH" in call_args
    assert graph_uri in call_args


async def test_list_named_graphs_parses_response(mock_sparql_client):
    """Mock QLever SELECT response is parsed into list of graph URI strings."""
    mock_sparql_client.bindings.return_value = [
        {"g": "usf://acme/context/finance/v1"},
        {"g": "usf://acme/context/risk/v1"},
    ]
    mock_sparql_client.query.return_value = {
        "results": {
            "bindings": [
                {"g": {"type": "uri", "value": "usf://acme/context/finance/v1"}},
                {"g": {"type": "uri", "value": "usf://acme/context/risk/v1"}},
            ]
        }
    }

    manager = NamedGraphManager(mock_sparql_client)
    graphs = await manager.list_graphs()

    assert isinstance(graphs, list)
    assert len(graphs) == 2
    assert "usf://acme/context/finance/v1" in graphs


async def test_count_triples_returns_int(mock_sparql_client):
    """Mock SELECT COUNT(*) response is parsed to an integer."""
    mock_sparql_client.bindings.return_value = [{"n": "42"}]
    mock_sparql_client.query.return_value = {
        "results": {"bindings": [{"n": {"type": "literal", "value": "42"}}]}
    }

    manager = NamedGraphManager(mock_sparql_client)
    count = await manager.triple_count("usf://acme/context/finance/v1")

    assert count == 42
    assert isinstance(count, int)


async def test_graph_exists_delegates_to_ask(mock_sparql_client):
    """graph_exists calls SPARQLClient.ask with ASK query."""
    mock_sparql_client.ask.return_value = True
    manager = NamedGraphManager(mock_sparql_client)

    result = await manager.graph_exists("usf://acme/context/finance/v1")

    mock_sparql_client.ask.assert_called_once()
    assert result is True


async def test_delete_graph_sends_drop(mock_sparql_client):
    """delete() sends SPARQL DROP GRAPH statement."""
    manager = NamedGraphManager(mock_sparql_client)
    await manager.delete("usf://acme/context/finance/v1")

    mock_sparql_client.update.assert_called_once()
    call_args = mock_sparql_client.update.call_args[0][0]
    assert "DROP GRAPH" in call_args


async def test_count_triples_empty_graph_returns_zero(mock_sparql_client):
    """When bindings are empty, triple_count returns 0."""
    mock_sparql_client.bindings.return_value = []
    manager = NamedGraphManager(mock_sparql_client)

    count = await manager.triple_count("usf://acme/context/empty/v1")
    assert count == 0
