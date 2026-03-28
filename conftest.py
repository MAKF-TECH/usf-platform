"""Root conftest — shared fixtures for all USF services."""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_qlever_client():
    client = AsyncMock()
    client.sparql_select = AsyncMock(return_value=[])
    client.insert_triples = AsyncMock(return_value=5)
    client.list_named_graphs = AsyncMock(return_value=[])
    client.graph_exists = AsyncMock(return_value=False)
    # SPARQLClient-compatible interface
    client.query = AsyncMock(return_value={"results": {"bindings": []}})
    client.update = AsyncMock(return_value=None)
    client.ask = AsyncMock(return_value=False)
    client.bindings = MagicMock(return_value=[])
    return client


@pytest.fixture
def mock_arcadedb_client():
    client = AsyncMock()
    client.execute_cypher = AsyncMock(return_value=[])
    client.upsert_node = AsyncMock(return_value="usf://test/entity/Test/abc123")
    client.vector_search = AsyncMock(return_value=[])
    client.traverse = AsyncMock(return_value=[])
    client.get_node = AsyncMock(return_value=None)
    return client


@pytest.fixture
def sample_fibo_triple():
    from rdflib import URIRef, Literal
    from packages.rdf.usf_rdf.triples import Triple
    return Triple(
        subject=URIRef("usf://acme/entity/Account/acc001"),
        predicate=URIRef("https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/hasBalance"),
        obj=Literal("50000.00"),
        graph="usf://acme/context/finance/v1",
    )


@pytest.fixture
def sample_token_claims():
    from usf_api.middleware.abac import TokenClaims
    return TokenClaims(
        sub="user-001",
        tenant_id="acme-bank",
        role="finance_analyst",
        department="treasury",
        clearance="internal",
    )
