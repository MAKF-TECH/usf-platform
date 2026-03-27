from __future__ import annotations
from typing import Any
from fastmcp import FastMCP
from loguru import logger
from usf_mcp.tools.metrics import explain_metric, list_metrics, query_metric
from usf_mcp.tools.entities import get_entity, search_entities
from usf_mcp.tools.contexts import list_contexts

mcp = FastMCP(
    name="USF — Universal Semantic Fabric",
    instructions=(
        "You have access to a governed, ontology-aligned knowledge graph for financial data. "
        "Use usf_list_contexts() to discover available semantic contexts. "
        "Use usf_list_metrics() to discover available metrics. "
        "Always set context when querying metrics that exist in multiple contexts. "
        "Call usf_explain_metric() to see valid contexts before querying."
    ),
)


@mcp.tool()
async def usf_list_metrics(context: str | None = None) -> list[dict[str, Any]]:
    """List all available semantic metrics. context: optional filter (e.g. 'risk', 'finance')."""
    return await list_metrics(context=context)


@mcp.tool()
async def usf_query_metric(metric: str, dimensions: list[str] | None = None,
                             filters: dict[str, Any] | None = None,
                             time_range: dict[str, str] | None = None,
                             context: str | None = None) -> dict[str, Any]:
    """
    Query a semantic metric. metric: from usf_list_metrics(). context: REQUIRED if metric in multiple contexts.
    dimensions: grouping (e.g. ['counterparty_name']). filters: equality (e.g. {'region': 'EU'}).
    time_range: {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}.
    """
    return await query_metric(metric=metric, dimensions=dimensions, filters=filters, time_range=time_range, context=context)


@mcp.tool()
async def usf_explain_metric(metric: str, context: str | None = None) -> dict[str, Any]:
    """Get full definition, SQL/SPARQL template, lineage, and valid contexts for a metric."""
    return await explain_metric(metric=metric, context=context)


@mcp.tool()
async def usf_search_entities(query: str, entity_type: str | None = None,
                                context: str | None = None) -> list[dict[str, Any]]:
    """Search entities in the knowledge graph. entity_type: e.g. 'fibo:CommercialBank'."""
    return await search_entities(query=query, entity_type=entity_type, context=context)


@mcp.tool()
async def usf_get_entity(iri: str) -> dict[str, Any]:
    """Get entity details by IRI (from usf_search_entities results)."""
    return await get_entity(iri=iri)


@mcp.tool()
async def usf_list_contexts() -> list[dict[str, Any]]:
    """List available semantic contexts. Use this before querying metrics."""
    return await list_contexts()


if __name__ == "__main__":
    from usf_mcp.config import settings
    mcp.run(transport="streamable-http", host="0.0.0.0", port=settings.mcp_port)
