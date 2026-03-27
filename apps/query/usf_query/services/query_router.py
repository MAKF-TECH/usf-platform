from __future__ import annotations

import re
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


# ── Routing heuristics ──────────────────────────────────────────────────────

def _needs_owl_inference(sparql: str) -> bool:
    """OWL inference needed: queries using RDFS/OWL entailment markers."""
    lower = sparql.lower()
    owl_markers = [
        "owl:class", "owl:objectproperty", "rdfs:subclassof",
        "rdfs:domain", "rdfs:range", "rdfs:subpropertyof",
        "owl:equivalentclass", "owl:restriction",
    ]
    return any(m in lower for m in owl_markers)


def _graph_traversal_depth(sparql: str) -> int:
    """
    Estimate graph traversal depth from SPARQL property path syntax.
    e.g. :p/:q/:r → depth 3, :p* → depth 99 (unbounded), :p{2,5} → depth 5
    """
    # Property path chaining: count '/' separators in path expressions
    # Match patterns like ?a :p/:q/:r ?b or ?a :p* ?b
    star_or_plus = re.search(r"[/:][*+]", sparql)
    if star_or_plus:
        return 99  # unbounded traversal

    # Count chained properties  (:p/:q/:r = depth 3)
    path_match = re.findall(r"\w+:\w+(?:/\w+:\w+)+", sparql)
    if path_match:
        longest = max(len(p.split("/")) for p in path_match)
        return longest

    # ArcadeDB traverse keywords
    traverse_kw = ["traverse", "shortestpath", "allshortestpaths", "path"]
    if any(kw in sparql.lower() for kw in traverse_kw):
        return 3  # assume deep traversal

    return 1


def _needs_vector_search(query: str) -> bool:
    """Vector similarity queries: NL mode or explicit vector markers."""
    lower = query.lower()
    vector_markers = [
        "similar to", "semantically", "nearest", "embedding",
        "vector_distance", "vectorindex", "cosine",
    ]
    return any(m in lower for m in vector_markers)


def _needs_r2rml_mapping(sparql: str) -> bool:
    """Queries touching relational data via virtual RDF → route to Ontop."""
    return "FROM <urn:usf:r2rml:" in sparql or "<urn:ontop:" in sparql


def _is_metric_sql_query(query: SemanticQuery) -> bool:
    """Standard metric query → Wren semantic SQL."""
    return query.query_type == QueryType.SQL


def _context_to_named_graph(context: str) -> str:
    return f"urn:usf:context:{context}"


# ── Main router ─────────────────────────────────────────────────────────────

class QueryRouter:
    """Route semantic queries to the appropriate backend."""

    def route(self, query: SemanticQuery) -> QueryBackend:
        """
        Routing rules (in priority order):
        1. Virtual KG (R2RML mapped) → ONTOP
        2. Standard metric/SQL query → WREN
        3. Vector similarity → ARCADEDB (vector index)
        4. Graph traversal depth > 2 → ARCADEDB (Cypher)
        5. OWL inference needed → QLEVER
        6. Default → QLEVER
        """
        q = query.query

        if query.query_type == QueryType.SQL:
            logger.debug("Router: SQL → WREN")
            return QueryBackend.WREN

        if query.query_type == QueryType.SPARQL:
            if _needs_r2rml_mapping(q):
                logger.debug("Router: R2RML → ONTOP")
                return QueryBackend.ONTOP

            if _needs_vector_search(q):
                logger.debug("Router: vector search → ARCADEDB")
                return QueryBackend.ARCADEDB

            depth = _graph_traversal_depth(q)
            if depth > 2:
                logger.debug("Router: graph depth %d → ARCADEDB", depth)
                return QueryBackend.ARCADEDB

            if _needs_owl_inference(q):
                logger.debug("Router: OWL inference → QLEVER")
                return QueryBackend.QLEVER

            logger.debug("Router: default → QLEVER")
            return QueryBackend.QLEVER

        # NL / OGRAG are handled upstream; fallback
        return QueryBackend.QLEVER


# Module-level router singleton
_router = QueryRouter()


async def route_query(query: SemanticQuery) -> QueryResult:
    """
    Route a semantic query to the appropriate backend and execute it.
    """
    backend = _router.route(query)

    if backend == QueryBackend.WREN:
        logger.info("Routing SQL query to Wren Engine", context=query.context)
        return await _wren.query(query.query)

    if backend == QueryBackend.ONTOP:
        logger.info("Routing SPARQL to Ontop (R2RML virtual RDF)", context=query.context)
        return await _ontop.query(query.query)

    if backend == QueryBackend.ARCADEDB:
        logger.info("Routing to ArcadeDB", context=query.context)
        if _needs_vector_search(query.query):
            # Parse out query question for embedding — fall back to Cypher
            result = await _arcadedb.cypher(query.query)
        else:
            result = await _arcadedb.cypher(query.query)
        return result

    # Default: QLever SPARQL
    logger.info("Routing SPARQL to QLever", context=query.context)
    named_graph = _context_to_named_graph(query.context) if query.context else None
    return await _qlever.query(query.query, named_graph=named_graph)


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
