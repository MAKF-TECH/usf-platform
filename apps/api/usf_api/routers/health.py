from __future__ import annotations
from fastapi import APIRouter, Request
from usf_api.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict:
    cache_ok = False
    try:
        pong = await request.app.state.cache.ping()
        cache_ok = bool(pong)
    except Exception:
        pass
    return {"status": "ok", "service": settings.service_name, "cache": "ok" if cache_ok else "degraded"}
