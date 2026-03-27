from __future__ import annotations
from typing import Any
import httpx
from loguru import logger
from usf_mcp.client import get_client


async def validate_metric_params(metric: str, dimensions: list[str],
                                   filters: dict[str, Any], context: str | None) -> tuple[bool, str]:
    try:
        client = get_client()
        metric_def = await client.explain_metric(metric, context)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return False, f"Metric '{metric}' not found."
        return False, f"Validation error: {exc}"
    except Exception as exc:
        return False, f"Validation error: {exc}"

    valid_dims: list[str] = metric_def.get("data", {}).get("dimensions", [])
    if valid_dims:
        bad = [d for d in dimensions if d not in valid_dims]
        if bad:
            return False, f"Invalid dimensions: {bad}. Valid: {valid_dims}"

    if context:
        valid_ctxs: list[str] = metric_def.get("data", {}).get("contexts", [])
        if valid_ctxs and context not in valid_ctxs:
            return False, f"Context '{context}' not valid for '{metric}'. Valid: {valid_ctxs}"

    return True, ""
