from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger

from usf_api.config import settings
from usf_api.middleware.abac import check_permission
from usf_api.middleware.context_router import resolve_context
from usf_api.middleware.response_envelope import wrap
from usf_api.routers.auth import get_current_user
from usf_api.services.cache import get_cached, make_metrics_cache_key, set_cached

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/")
async def list_metrics(
    request: Request,
    claims: Annotated[dict, Depends(get_current_user)],
    x_usf_context: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """List all available metrics for this tenant, filtered by ABAC."""
    tenant_id = claims["tenant_id"]
    user_id = claims["sub"]
    role = claims["role"]

    context = await resolve_context(x_usf_context, tenant_id)

    abac_result = await check_permission(
        user_id=user_id, tenant_id=tenant_id, role=role,
        action="read", resource="metrics",
    )
    if not abac_result.get("allow"):
        raise HTTPException(status_code=403, detail="Access denied")

    cache_key = make_metrics_cache_key(tenant_id, context or "")
    cached = await get_cached(cache_key, request.app.state.cache)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.usf_kg_url}/metrics",
                params={"tenant_id": tenant_id, "context": context},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"KG service error: {exc}")

    result = wrap(data=data)
    await set_cached(cache_key, result, request.app.state.cache)
    return result


@router.get("/{name}")
async def get_metric(
    name: str,
    request: Request,
    claims: Annotated[dict, Depends(get_current_user)],
    x_usf_context: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Get a specific metric definition with ABAC check."""
    tenant_id = claims["tenant_id"]
    user_id = claims["sub"]
    role = claims["role"]

    context = await resolve_context(x_usf_context, tenant_id, metric_name=name)

    abac_result = await check_permission(
        user_id=user_id, tenant_id=tenant_id, role=role,
        action="read", resource="metric",
        resource_attrs={"name": name, "context": context},
    )
    if not abac_result.get("allow"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get metric explanation from usf-query
            resp = await client.get(f"{settings.usf_query_url}/explain/{name}")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Query service error: {exc}")

    return wrap(data=data)
