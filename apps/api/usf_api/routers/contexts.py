from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from usf_api.config import settings
from usf_api.middleware.response_envelope import wrap
from usf_api.routers.auth import get_current_user

router = APIRouter(prefix="/contexts", tags=["contexts"])


@router.get(
    "/",
    summary="List available semantic contexts",
    description="Return all semantic contexts available for the authenticated tenant. Contexts scope queries to specific named graphs in the knowledge graph.",
    responses={
        200: {"description": "List of contexts"},
        502: {"description": "KG service unavailable"},
    },
    tags=["contexts"],
)
async def list_contexts(
    request: Request,
    claims: Annotated[dict, Depends(get_current_user)],
) -> dict[str, Any]:
    """List all available contexts for this tenant/user."""
    tenant_id = claims["tenant_id"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.usf_kg_url}/contexts",
                params={"tenant_id": tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"KG service error: {exc}")

    return wrap(data=data)
