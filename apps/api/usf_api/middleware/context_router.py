from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, Request
from loguru import logger

from usf_api.config import settings


class ContextAmbiguousError(HTTPException):
    def __init__(self, metric: str | None, available_contexts: list[str]) -> None:
        super().__init__(
            status_code=409,
            detail={
                "error": "context_ambiguous",
                "metric": metric,
                "available_contexts": available_contexts,
                "hint": "Set X-USF-Context header",
            },
        )


async def _get_tenant_contexts(tenant_id: str) -> list[str]:
    """Fetch available contexts for this tenant from usf-kg."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.usf_kg_url}/contexts",
                params={"tenant_id": tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return [c["name"] for c in data.get("contexts", [])]
    except Exception as exc:
        logger.warning("Failed to fetch tenant contexts", error=str(exc))
        return []


async def _get_contexts_for_metric(tenant_id: str, metric_name: str) -> list[str]:
    """Fetch all contexts that define this metric for this tenant."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.usf_kg_url}/metrics/{metric_name}/contexts",
                params={"tenant_id": tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("contexts", [])
    except Exception as exc:
        logger.warning("Failed to fetch metric contexts", error=str(exc), metric=metric_name)
        return []


async def resolve_context(
    context_header: str | None,
    tenant_id: str,
    metric_name: str | None = None,
) -> str:
    """
    Resolve the context for this request.
    
    Rules:
    1. If X-USF-Context provided → validate it exists → return
    2. If None and only one context for tenant → return that (with warning)
    3. If None and multiple contexts define same metric → raise 409

    409 body: {"error": "context_ambiguous", "metric": ..., "available_contexts": [...], "hint": "Set X-USF-Context header"}
    """
    if context_header:
        # Validate it exists
        tenant_contexts = await _get_tenant_contexts(tenant_id)
        if tenant_contexts and context_header not in tenant_contexts:
            raise HTTPException(
                status_code=404,
                detail=f"Context '{context_header}' not found for this tenant.",
            )
        logger.debug("Context resolved from header", context=context_header, tenant_id=tenant_id)
        return context_header

    # No context header: check metric ambiguity
    if metric_name:
        metric_contexts = await _get_contexts_for_metric(tenant_id, metric_name)
        if len(metric_contexts) == 0:
            # Metric not found in any context — let downstream handle
            return "default"
        if len(metric_contexts) == 1:
            logger.warning(
                "Context inferred from single match",
                context=metric_contexts[0],
                metric=metric_name,
                warning="X-USF-Context header not set",
            )
            return metric_contexts[0]
        # Multiple contexts define this metric → ambiguous
        raise ContextAmbiguousError(
            metric=metric_name,
            available_contexts=metric_contexts,
        )

    # No metric either: use tenant default context
    tenant_contexts = await _get_tenant_contexts(tenant_id)
    if len(tenant_contexts) == 1:
        return tenant_contexts[0]
    if len(tenant_contexts) == 0:
        return "default"

    raise ContextAmbiguousError(metric=None, available_contexts=tenant_contexts)
