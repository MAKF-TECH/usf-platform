from __future__ import annotations

from typing import Any

from loguru import logger

from usf_query.models import QueryBackend, QueryResult, SemanticQuery, QueryType
from usf_query.services.qlever_client import QLeverClient
from usf_query.services.arcadedb_client import ArcadeDBClient
from usf_query.services.wren_client import WrenClient
from usf_query.services.ontop_client import OntopClient

# Singleton clients (created once, reused across requests)
_qlever = QLeverClient()
_arcadedb = ArcadeDBClient()
_wren = WrenClient()
_ontop = OntopClient()


def _is_graph_query(sparql: str) -> bool:
    """Heuristic: SPARQL with path traversal or graph patterns → ArcadeDB."""
    lower = sparql.lower()
    return any(kw in lower for kw in ["path", "traverse", "shortestpath", "allshortestpaths"])


def _is_property_graph_query(query: str) -> bool:
    """Detect Cypher syntax."""
    lower = query.lower()
    return "match" in lower and "return" in lower and "where" in lower


def _needs_r2rml_mapping(sparql: str) -> bool:
    """If the query touches relational data via virtual RDF → route to Ontop."""
    return "FROM <urn:usf:r2rml:" in sparql


async def route_query(query: SemanticQuery) -> QueryResult:
    """
    Route a semantic query to the appropriate backend:
    - QLever: pure SPARQL over materialized RDF triples (named graphs)
    - ArcadeDB: graph traversal, Cypher, vector search
    - Wren: semantic SQL with MDL business model
    - Ontop: SPARQL over virtual RDF view of relational DB (R2RML)
    - hybrid: split query across multiple backends and merge
    """
    if query.query_type == QueryType.SQL:
        logger.info("Routing SQL query to Wren Engine", context=query.context)
        return await _wren.query(query.query)

    if query.query_type == QueryType.SPARQL:
        sparql = query.query

        if _needs_r2rml_mapping(sparql):
            logger.info("Routing SPARQL to Ontop (R2RML virtual RDF)", context=query.context)
            return await _ontop.query(sparql)

        if _is_graph_query(sparql):
            logger.info("Routing SPARQL graph traversal to ArcadeDB", context=query.context)
            # Convert SPARQL path query to Cypher (simplified pass-through for now)
            return await _arcadedb.cypher(sparql)

        logger.info("Routing SPARQL to QLever", context=query.context)
        named_graph = _context_to_named_graph(query.context) if query.context else None
        return await _qlever.query(sparql, named_graph=named_graph)

    # NL and OGRAG are handled by their own service layers (nl2sparql.py, ograg.py)
    raise ValueError(f"Unexpected query type for route_query: {query.query_type}")


def _context_to_named_graph(context: str) -> str:
    """Convert context name to QLever named graph URI."""
    return f"urn:usf:context:{context}"


async def backends_health() -> dict[str, bool]:
    """Check health of all backends."""
    return {
        "qlever": await _qlever.health(),
        "arcadedb": await _arcadedb.health(),
        "wren": await _wren.health(),
        "ontop": await _ontop.health(),
    }


def get_qlever() -> QLeverClient:
    return _qlever


def get_arcadedb() -> ArcadeDBClient:
    return _arcadedb
