from __future__ import annotations
from typing import Annotated, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from usf_api.config import settings
from usf_api.middleware.abac import check_permission
from usf_api.middleware.response_envelope import wrap
from usf_api.routers.auth import get_current_user

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("/search")
async def search_entities(request: Request, claims: Annotated[dict, Depends(get_current_user)],
                           q: str = Query(...), entity_type: str | None = Query(None),
                           context: str | None = Query(None), limit: int = Query(default=20, le=100)) -> dict[str, Any]:
    abac = await check_permission(user_id=claims["sub"], tenant_id=claims["tenant_id"], role=claims["role"], action="read", resource="entity")
    if not abac.get("allow"):
        raise HTTPException(status_code=403, detail="Access denied")
    params: dict[str, Any] = {"q": q, "tenant_id": claims["tenant_id"], "limit": limit}
    if entity_type: params["entity_type"] = entity_type
    if context: params["context"] = context
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{settings.usf_kg_url}/entities/search", params=params)
        resp.raise_for_status()
    return wrap(data=resp.json())
