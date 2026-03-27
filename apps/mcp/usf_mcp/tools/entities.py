from __future__ import annotations

from typing import Any

from loguru import logger

from usf_mcp.client import get_client


async def search_entities(
    query: str,
    entity_type: str | None = None,
    context: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search for entities in the knowledge graph by name, type, or semantic similarity.
    
    Args:
        query: Search query (e.g. 'Deutsche Bank', 'EU financial institutions')
        entity_type: Optional ontology type filter (e.g. 'fibo:CommercialBank', 'fibo:Account')
        context: Optional context to scope the search
    
    Returns: List of matching entities with IRI, name, type, and description.
    """
    client = get_client()
    result = await client.search_entities(query=query, entity_type=entity_type, context=context)
    entities = result.get("data", {}).get("entities", result.get("data", []))
    logger.info("MCP search_entities", query=query, count=len(entities))
    return entities


async def get_entity(iri: str) -> dict[str, Any]:
    """
    Retrieve detailed information about a specific entity by its IRI.
    
    Args:
        iri: Entity IRI (e.g. 'urn:usf:entity:bank:deutsche-bank-ag')
    
    Returns: Entity detail with properties, relationships, and PROV-O provenance.
    """
    client = get_client()
    result = await client.get_entity(iri)
    logger.info("MCP get_entity", iri=iri)
    return result.get("data", result)
