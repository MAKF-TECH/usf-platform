from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from loguru import logger

from usf_api.config import settings
from usf_api.middleware.abac import check_permission
from usf_api.middleware.response_envelope import wrap
from usf_api.routers.auth import get_current_user

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get(
    "/search",
    summary="Search knowledge graph entities",
    description="Full-text and semantic entity search forwarded to the USF Knowledge Graph service. Supports filtering by entity type and context. Subject to ABAC.",
    responses={
        200: {"description": "Search results"},
        403: {"description": "ABAC denied"},
        502: {"description": "KG service unavailable"},
    },
    tags=["entities"],
)
async def search_entities(
    request: Request,
    claims: Annotated[dict, Depends(get_current_user)],
    q: str = Query(..., description="Search query"),
    entity_type: str | None = Query(None),
    context: str | None = Query(None),
    limit: int = Query(default=20, le=100),
) -> dict[str, Any]:
    """Full-text + semantic entity search forwarded to usf-kg."""
    tenant_id = claims["tenant_id"]
    user_id = claims["sub"]
    role = claims["role"]

    abac_result = await check_permission(
        user_id=user_id, tenant_id=tenant_id, role=role,
        action="read", resource="entity",
    )
    if not abac_result.get("allow"):
        raise HTTPException(status_code=403, detail="Access denied")

    params: dict[str, Any] = {
        "q": q,
        "tenant_id": tenant_id,
        "limit": limit,
    }
    if entity_type:
        params["entity_type"] = entity_type
    if context:
        params["context"] = context

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.usf_kg_url}/entities/search",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"KG service error: {exc}")

    return wrap(data=data)
