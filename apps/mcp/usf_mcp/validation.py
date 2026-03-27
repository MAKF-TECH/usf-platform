from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from usf_mcp.client import get_client
from usf_mcp.config import settings


async def _fetch_ontology_classes(context: str | None) -> list[str]:
    """Fetch valid ontology class names for the given context from usf-api."""
    try:
        client = get_client()
        data = await client.get("/contexts/")
        return [c.get("ontology_class", "") for c in data.get("data", {}).get("contexts", [])]
    except Exception:
        return []


async def validate_metric_params(
    metric: str,
    dimensions: list[str],
    filters: dict[str, Any],
    context: str | None,
) -> tuple[bool, str]:
    """
    Pre-execution semantic validation.
    Checks LLM-generated parameters against ontology before forwarding.
    
    Returns (is_valid, error_message).
    """
    # Step 1: verify metric exists
    try:
        client = get_client()
        metric_def = await client.explain_metric(metric, context)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return False, f"Metric '{metric}' not found. Check list_metrics() for available metrics."
        return False, f"Failed to fetch metric definition: {exc}"
    except Exception as exc:
        return False, f"Validation error: {exc}"

    # Step 2: verify dimensions are valid for this metric
    valid_dims: list[str] = metric_def.get("data", {}).get("dimensions", [])
    if valid_dims:
        invalid_dims = [d for d in dimensions if d not in valid_dims]
        if invalid_dims:
            return False, (
                f"Invalid dimensions: {invalid_dims}. "
                f"Valid dimensions for '{metric}': {valid_dims}"
            )

    # Step 3: verify context is valid (if provided)
    if context:
        valid_contexts: list[str] = metric_def.get("data", {}).get("contexts", [])
        if valid_contexts and context not in valid_contexts:
            return False, (
                f"Context '{context}' is not valid for metric '{metric}'. "
                f"Valid contexts: {valid_contexts}"
            )

    logger.debug(
        "MCP validation passed",
        metric=metric,
        dimensions=dimensions,
        context=context,
    )
    return True, ""
