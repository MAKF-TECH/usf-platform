from __future__ import annotations

from typing import Any

from loguru import logger

from usf_mcp.client import get_client
from usf_mcp.validation import validate_metric_params


async def list_metrics(context: str | None = None) -> list[dict[str, Any]]:
    """
    List all available metrics for the current tenant.
    
    Args:
        context: Optional context name (e.g. 'risk', 'finance', 'ops').
                 If not provided, lists all metrics across all contexts.
    
    Returns: List of metric descriptors with name, description, and contexts.
    """
    client = get_client()
    try:
        data = await client.list_metrics(context=context)
        metrics = data.get("data", {}).get("metrics", data.get("data", []))
        logger.info("MCP list_metrics", count=len(metrics), context=context)
        return metrics
    except Exception as exc:
        logger.error("MCP list_metrics failed", error=str(exc))
        raise


async def query_metric(
    metric: str,
    dimensions: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    time_range: dict[str, str] | None = None,
    context: str | None = None,
) -> dict[str, Any]:
    """
    Query a semantic metric by name with optional dimensions, filters, and time range.
    
    Args:
        metric: Metric name (e.g. 'total_exposure_by_counterparty')
        dimensions: Grouping dimensions (e.g. ['counterparty_name', 'currency'])
        filters: Key-value filter conditions (e.g. {'region': 'EU'})
        time_range: Time range dict with 'start' and 'end' (ISO dates)
        context: Semantic context (e.g. 'risk'). Required if metric exists in multiple contexts.
    
    Returns: Query result with rows, columns, and provenance.
    """
    dims = dimensions or []
    fltrs = filters or {}

    # Pre-execution semantic validation
    is_valid, error_msg = await validate_metric_params(metric, dims, fltrs, context)
    if not is_valid:
        raise ValueError(f"Validation failed: {error_msg}")

    client = get_client()
    result = await client.query_metric(
        metric=metric,
        dimensions=dims,
        filters=fltrs,
        time_range=time_range,
        context=context,
    )

    logger.info(
        "MCP query_metric",
        metric=metric,
        context=context,
        rows=result.get("data", {}).get("total_rows", "?"),
    )
    return result


async def explain_metric(
    metric: str,
    context: str | None = None,
) -> dict[str, Any]:
    """
    Get the full definition, SQL/SPARQL templates, lineage, and ontology class for a metric.
    
    Args:
        metric: Metric name
        context: Optional context for context-specific details
    
    Returns: Metric definition with SQL template, SPARQL template, dimensions, and lineage.
    """
    client = get_client()
    result = await client.explain_metric(metric, context)
    logger.info("MCP explain_metric", metric=metric, context=context)
    return result
