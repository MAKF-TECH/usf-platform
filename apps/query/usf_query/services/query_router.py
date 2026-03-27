from __future__ import annotations
from loguru import logger
from usf_query.models import QueryBackend, QueryResult, SemanticQuery, QueryType
from usf_query.services.qlever_client import QLeverClient
from usf_query.services.arcadedb_client import ArcadeDBClient
from usf_query.services.wren_client import WrenClient
from usf_query.services.ontop_client import OntopClient

_qlever = QLeverClient()
_arcadedb = ArcadeDBClient()
_wren = WrenClient()
_ontop = OntopClient()


def _is_graph_query(sparql: str) -> bool:
    lower = sparql.lower()
    return any(kw in lower for kw in ["path", "traverse", "shortestpath", "allshortestpaths"])


def _needs_r2rml(sparql: str) -> bool:
    return "FROM <urn:usf:r2rml:" in sparql


async def route_query(query: SemanticQuery) -> QueryResult:
    """Route to appropriate backend based on query type and content."""
    if query.query_type == QueryType.SQL:
        logger.info("Routing → Wren", context=query.context)
        return await _wren.query(query.query)

    if query.query_type == QueryType.SPARQL:
        if _needs_r2rml(query.query):
            logger.info("Routing → Ontop (R2RML)", context=query.context)
            return await _ontop.query(query.query)
        if _is_graph_query(query.query):
            logger.info("Routing → ArcadeDB (graph traversal)", context=query.context)
            return await _arcadedb.cypher(query.query)
        named_graph = f"urn:usf:context:{query.context}" if query.context else None
        logger.info("Routing → QLever", context=query.context)
        return await _qlever.query(query.query, named_graph=named_graph)

    raise ValueError(f"Unexpected query type for route_query: {query.query_type}")


async def backends_health() -> dict[str, bool]:
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
