from __future__ import annotations
from typing import Any
from loguru import logger
from usf_mcp.client import get_client
from usf_mcp.validation import validate_metric_params


async def list_metrics(context: str | None = None) -> list[dict[str, Any]]:
    client = get_client()
    data = await client.list_metrics(context=context)
    metrics = data.get("data", {}).get("metrics", data.get("data", []))
    logger.info("MCP list_metrics", count=len(metrics))
    return metrics


async def query_metric(metric: str, dimensions: list[str] | None = None,
                        filters: dict[str, Any] | None = None, time_range: dict[str, str] | None = None,
                        context: str | None = None) -> dict[str, Any]:
    dims = dimensions or []
    fltrs = filters or {}
    valid, err = await validate_metric_params(metric, dims, fltrs, context)
    if not valid:
        raise ValueError(f"Validation failed: {err}")
    return await get_client().query_metric(metric=metric, dimensions=dims, filters=fltrs, time_range=time_range, context=context)


async def explain_metric(metric: str, context: str | None = None) -> dict[str, Any]:
    return await get_client().explain_metric(metric, context)
