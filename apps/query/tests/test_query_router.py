"""Tests for QueryRouter — routing heuristics across backends."""
import pytest

from usf_query.models import SemanticQuery, QueryType, QueryBackend
from usf_query.services.query_router import QueryRouter


def _make_query(query_type: QueryType, query: str = "SELECT ?s ?p ?o WHERE { ?s ?p ?o }") -> SemanticQuery:
    return SemanticQuery(query=query, query_type=query_type)


def test_vector_search_routes_to_arcadedb():
    """SPARQL query with vector similarity markers routes to ArcadeDB."""
    query = _make_query(
        QueryType.SPARQL,
        "SELECT ?s WHERE { ?s ex:embedding ?e . FILTER(vector_distance(?e, ?q) < 0.1) }",
    )
    result = QueryRouter().route(query)
    assert result == QueryBackend.ARCADEDB


def test_deep_traversal_routes_to_arcadedb():
    """SPARQL query with deep property path (depth > 2) routes to ArcadeDB."""
    query = _make_query(
        QueryType.SPARQL,
        "SELECT ?s ?o WHERE { ?s :rel/:sub/:obj ?o }",  # depth=3 chained path
    )
    result = QueryRouter().route(query)
    assert result == QueryBackend.ARCADEDB


def test_metric_sql_routes_to_wren():
    """SQL query type routes to Wren semantic engine."""
    query = _make_query(
        QueryType.SQL,
        "SELECT SUM(balance) FROM accounts",
    )
    result = QueryRouter().route(query)
    assert result == QueryBackend.WREN


def test_default_routes_to_qlever():
    """Plain SPARQL without special markers routes to QLever."""
    query = _make_query(
        QueryType.SPARQL,
        "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
    )
    result = QueryRouter().route(query)
    assert result == QueryBackend.QLEVER


def test_owl_inference_routes_to_qlever():
    """SPARQL using OWL/RDFS entailment markers routes to QLever (not ArcadeDB)."""
    query = _make_query(
        QueryType.SPARQL,
        "SELECT ?sub WHERE { ?sub rdfs:subClassOf owl:Class }",
    )
    result = QueryRouter().route(query)
    assert result == QueryBackend.QLEVER


def test_r2rml_routes_to_ontop():
    """SPARQL query referencing R2RML virtual RDF namespace routes to Ontop."""
    query = _make_query(
        QueryType.SPARQL,
        "SELECT ?s WHERE { GRAPH <urn:usf:r2rml:accounts> { ?s ?p ?o } }",
    )
    result = QueryRouter().route(query)
    assert result == QueryBackend.ONTOP


def test_unbounded_traversal_routes_to_arcadedb():
    """SPARQL query with property path star (*) routes to ArcadeDB (unbounded depth)."""
    query = _make_query(
        QueryType.SPARQL,
        "SELECT ?s ?o WHERE { ?s ex:rel* ?o }",
    )
    result = QueryRouter().route(query)
    assert result == QueryBackend.ARCADEDB
