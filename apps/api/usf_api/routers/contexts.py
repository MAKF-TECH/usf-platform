from __future__ import annotations
from typing import Annotated, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from usf_api.config import settings
from usf_api.middleware.response_envelope import wrap
from usf_api.routers.auth import get_current_user

router = APIRouter(prefix="/contexts", tags=["contexts"])


@router.get("/")
async def list_contexts(request: Request, claims: Annotated[dict, Depends(get_current_user)]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.usf_kg_url}/contexts", params={"tenant_id": claims["tenant_id"]})
        resp.raise_for_status()
    return wrap(data=resp.json())
