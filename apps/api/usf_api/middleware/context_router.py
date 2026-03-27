from __future__ import annotations
import httpx
from fastapi import HTTPException
from loguru import logger
from usf_api.config import settings


async def _tenant_contexts(tenant_id: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.usf_kg_url}/contexts", params={"tenant_id": tenant_id})
            resp.raise_for_status()
            return [c["name"] for c in resp.json().get("contexts", [])]
    except Exception as exc:
        logger.warning("Failed to fetch contexts", error=str(exc))
        return []


async def _metric_contexts(tenant_id: str, metric: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.usf_kg_url}/metrics/{metric}/contexts", params={"tenant_id": tenant_id})
            resp.raise_for_status()
            return resp.json().get("contexts", [])
    except Exception as exc:
        logger.warning("Failed to fetch metric contexts", error=str(exc), metric=metric)
        return []


async def resolve_context(context_header: str | None, tenant_id: str, metric_name: str | None = None) -> str:
    """
    Resolve context with 409 on ambiguity (CRITICAL):
    - Header provided → validate and return
    - None + 1 metric context → return with warning
    - None + multiple metric contexts → raise 409
    """
    if context_header:
        all_ctxs = await _tenant_contexts(tenant_id)
        if all_ctxs and context_header not in all_ctxs:
            raise HTTPException(status_code=404, detail=f"Context '{context_header}' not found")
        return context_header

    if metric_name:
        ctxs = await _metric_contexts(tenant_id, metric_name)
        if len(ctxs) == 1:
            logger.warning("Context inferred (no header set)", context=ctxs[0], metric=metric_name)
            return ctxs[0]
        if len(ctxs) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "context_ambiguous",
                    "metric": metric_name,
                    "available_contexts": ctxs,
                    "hint": "Set X-USF-Context header",
                },
            )

    all_ctxs = await _tenant_contexts(tenant_id)
    if len(all_ctxs) == 1:
        return all_ctxs[0]
    if len(all_ctxs) > 1:
        raise HTTPException(
            status_code=409,
            detail={"error": "context_ambiguous", "available_contexts": all_ctxs, "hint": "Set X-USF-Context header"},
        )
    return "default"
