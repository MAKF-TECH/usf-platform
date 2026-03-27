from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from usf_api.config import settings


class ContextResolution(BaseModel):
    """Result of context resolution for a request."""
    context: str
    named_graph: str
    inferred: bool = False  # True if context was auto-resolved (no header)


class ContextAmbiguousError(HTTPException):
    def __init__(self, metric: str | None, available_contexts: list[str]) -> None:
        super().__init__(
            status_code=409,
            detail={
                "error": "context_ambiguous",
                "metric": metric,
                "available_contexts": available_contexts,
                "hint": "Set X-USF-Context header to one of the above",
            },
        )


def _named_graph(tenant_id: str, context: str) -> str:
    return f"usf://{tenant_id}/context/{context}/latest"


async def context_exists(context: str, tenant_id: str) -> bool:
    """Return True if the named context exists for this tenant."""
    contexts = await _get_tenant_contexts(tenant_id)
    return not contexts or context in contexts


async def get_contexts_for_metric(metric: str, tenant_id: str) -> list[str]:
    """Fetch all contexts that define this metric for this tenant."""
    return await _get_contexts_for_metric(tenant_id, metric)


async def get_default_context(tenant_id: str) -> ContextResolution:
    """Return the default context for a tenant (first/only context, or 'default')."""
    contexts = await _get_tenant_contexts(tenant_id)
    name = contexts[0] if len(contexts) == 1 else "default"
    return ContextResolution(
        context=name,
        named_graph=_named_graph(tenant_id, name),
        inferred=True,
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


def extract_metric_from_request(request: Request) -> str | None:
    """Extract metric name from request body (cached in state if available)."""
    return getattr(request.state, "metric", None)


async def resolve_context(
    request: Request | None = None,
    context_header: str | None = None,
    tenant_id: str = "default",
    metric_name: str | None = None,
) -> ContextResolution:
    """
    Resolve the context for this request.

    Rules (priority order):
    1. X-USF-Context header provided → validate it exists → return
    2. Metric provided → look up contexts → disambiguate or infer
    3. Fall back to tenant default context

    Raises:
        HTTPException(404) if given context doesn't exist
        HTTPException(409) if metric maps to multiple contexts
    """
    # Allow both calling styles: resolve_context(request) or resolve_context(context_header=..., tenant_id=...)
    if request is not None and context_header is None:
        context_header = request.headers.get("X-USF-Context")
        tenant_id = getattr(request.state, "tenant_id", "default")
        metric_name = metric_name or extract_metric_from_request(request)

    if context_header:
        if not await context_exists(context_header, tenant_id):
            raise HTTPException(
                status_code=404,
                detail=f"Context '{context_header}' not found for this tenant.",
            )
        logger.debug("Context resolved from header", context=context_header, tenant_id=tenant_id)
        return ContextResolution(
            context=context_header,
            named_graph=_named_graph(tenant_id, context_header),
            inferred=False,
        )

    # No context header: check metric ambiguity
    if metric_name:
        metric_contexts = await _get_contexts_for_metric(tenant_id, metric_name)
        if len(metric_contexts) == 0:
            # Metric not found in any context — fall through to tenant default
            pass
        elif len(metric_contexts) == 1:
            ctx = metric_contexts[0]
            logger.warning(
                "Context inferred from single metric match",
                context=ctx,
                metric=metric_name,
                hint="Set X-USF-Context header to suppress this warning",
            )
            return ContextResolution(
                context=ctx,
                named_graph=_named_graph(tenant_id, ctx),
                inferred=True,
            )
        else:
            raise ContextAmbiguousError(
                metric=metric_name,
                available_contexts=metric_contexts,
            )

    # Fall back to tenant default
    return await get_default_context(tenant_id)
