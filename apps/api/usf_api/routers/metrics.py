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


@router.get(
    "/",
    summary="List available metrics",
    description="List all available semantic metrics for the authenticated tenant. Results are filtered by ABAC policy and optionally scoped by context via `X-USF-Context` header. Responses are cached.",
    responses={
        200: {"description": "List of available metrics"},
        403: {"description": "ABAC denied — insufficient permissions"},
        502: {"description": "KG service unavailable"},
    },
    tags=["metrics"],
)
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


@router.get(
    "/{name}",
    summary="Get metric definition and lineage",
    description="Retrieve a specific metric definition including ontology mapping, SQL/SPARQL templates, available contexts, and data lineage. Subject to ABAC and context resolution.",
    responses={
        200: {"description": "Metric definition with lineage"},
        403: {"description": "ABAC denied"},
        404: {"description": "Metric not found"},
        409: {"description": "Context ambiguous for this metric"},
        502: {"description": "Query service unavailable"},
    },
    tags=["metrics"],
)
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
