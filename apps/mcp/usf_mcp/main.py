from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from loguru import logger

from usf_mcp.config import settings
from usf_mcp.tools.metrics import explain_metric, list_metrics, query_metric
from usf_mcp.tools.entities import get_entity, search_entities
from usf_mcp.tools.contexts import list_contexts

mcp = FastMCP(
    name="USF — Universal Semantic Fabric",
    instructions=(
        "You have access to a governed, ontology-aligned knowledge graph for financial data. "
        "Use list_contexts() to discover available semantic contexts. "
        "Use list_metrics() to discover what metrics are available. "
        "Always set context when querying metrics that exist in multiple contexts — "
        "if you're unsure, call list_contexts() first, then explain_metric() to see valid contexts. "
        "Use search_entities() to find entities (banks, accounts, transactions) in the knowledge graph."
    ),
)


@mcp.tool()
async def usf_list_metrics(context: str | None = None) -> list[dict[str, Any]]:
    """
    List all available semantic metrics.
    
    Args:
        context: Optional context filter (e.g. 'risk', 'finance'). 
                 If omitted, all metrics are returned.
    """
    return await list_metrics(context=context)


@mcp.tool()
async def usf_query_metric(
    metric: str,
    dimensions: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    time_range: dict[str, str] | None = None,
    context: str | None = None,
) -> dict[str, Any]:
    """
    Query a semantic metric and get aggregated results.
    
    Args:
        metric: Metric name from list_metrics() (e.g. 'total_exposure_by_counterparty')
        dimensions: Grouping dimensions (e.g. ['counterparty_name', 'region'])
        filters: Equality filters as key-value pairs (e.g. {'currency': 'EUR', 'region': 'EU'})
        time_range: Time range as {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}
        context: Semantic context. REQUIRED if metric exists in multiple contexts.
                 Use explain_metric() to find valid contexts.
    """
    return await query_metric(
        metric=metric,
        dimensions=dimensions,
        filters=filters,
        time_range=time_range,
        context=context,
    )


@mcp.tool()
async def usf_explain_metric(metric: str, context: str | None = None) -> dict[str, Any]:
    """
    Get full definition, SQL/SPARQL template, lineage, and ontology mapping for a metric.
    
    Args:
        metric: Metric name
        context: Optional context for context-specific details
    """
    return await explain_metric(metric=metric, context=context)


@mcp.tool()
async def usf_search_entities(
    query: str,
    entity_type: str | None = None,
    context: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search for entities in the knowledge graph.
    
    Args:
        query: Search text (e.g. 'Deutsche Bank', 'EU banks with AML exposure')
        entity_type: Optional ontology type filter (e.g. 'fibo:CommercialBank')
        context: Optional context scope
    """
    return await search_entities(query=query, entity_type=entity_type, context=context)


@mcp.tool()
async def usf_get_entity(iri: str) -> dict[str, Any]:
    """
    Get detailed information about a specific entity by IRI.
    
    Args:
        iri: Entity IRI (from search_entities results)
    """
    return await get_entity(iri=iri)


@mcp.tool()
async def usf_list_contexts() -> list[dict[str, Any]]:
    """
    List all available semantic contexts for this tenant.
    Use this to discover valid context names before querying metrics.
    """
    return await list_contexts()


if __name__ == "__main__":
    from usf_mcp.config import settings
    mcp.run(transport="streamable-http", host="0.0.0.0", port=settings.mcp_port)

# ── OpenTelemetry instrumentation ─────────────────────────────────────────────
import os as _os

def _configure_telemetry(service_name: str):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    provider = TracerProvider()
    otlp_endpoint = _os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

try:
    _configure_telemetry("usf-mcp")
except ImportError:
    pass
