from __future__ import annotations
import hashlib, uuid
from typing import Annotated, Any
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger
from usf_api.config import settings
from usf_api.middleware.abac import check_permission
from usf_api.middleware.context_router import resolve_context
from usf_api.middleware.prov_emitter import build_prov_o
from usf_api.middleware.response_envelope import wrap
from usf_api.models import QueryRequest
from usf_api.routers.auth import get_current_user
from usf_api.services.cache import get_cached, make_query_cache_key, set_cached

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/")
async def run_query(
    req: QueryRequest,
    request: Request,
    claims: Annotated[dict, Depends(get_current_user)],
    x_usf_context: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    user_id = claims["sub"]
    tenant_id = claims["tenant_id"]
    role = claims["role"]
    query_id = str(uuid.uuid4())

    context = await resolve_context(x_usf_context, tenant_id, metric_name=req.metric)

    abac = await check_permission(user_id=user_id, tenant_id=tenant_id, role=role,
                                   action="query", resource="metric",
                                   resource_attrs={"name": req.metric, "context": context})
    if not abac.get("allow"):
        raise HTTPException(status_code=403, detail="Access denied by ABAC policy")

    query_hash = hashlib.sha256(str(req.model_dump()).encode()).hexdigest()[:16]
    cache_key = make_query_cache_key(tenant_id, context or "", query_hash)
    cached = await get_cached(cache_key, request.app.state.cache)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if req.question:
                resp = await client.post(f"{settings.usf_query_url}/execute/nl",
                    json={"question": req.question, "context": context, "tenant_id": tenant_id, "ontology_context": "", "max_results": req.max_results})
            elif req.sparql:
                resp = await client.post(f"{settings.usf_query_url}/execute/sparql",
                    json={"query": req.sparql, "query_type": "sparql", "context": context, "tenant_id": tenant_id})
            elif req.sql:
                resp = await client.post(f"{settings.usf_query_url}/execute/sql",
                    json={"query": req.sql, "query_type": "sql", "context": context, "tenant_id": tenant_id})
            elif req.metric:
                cr = await client.post(f"{settings.usf_query_url}/compile/",
                    json={"metric_name": req.metric, "context": context, "tenant_id": tenant_id, "dialect": "postgres"})
                cr.raise_for_status()
                compiled = cr.json()
                resp = await client.post(f"{settings.usf_query_url}/execute/sql",
                    json={"query": compiled["sql"], "query_type": "sql", "context": context})
            else:
                raise HTTPException(status_code=422, detail="Provide question, sparql, sql, or metric")
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPError as exc:
        logger.error("usf-query failed", error=str(exc), query_id=query_id)
        raise HTTPException(status_code=502, detail=f"Query service error: {exc}")

    prov = build_prov_o(query_id=query_id, user_id=user_id, tenant_id=tenant_id, context=context,
                        query_hash=query_hash, abac_decision="permit", backend=result.get("backend_used"))
    response = wrap(data=result)
    response["provenance"] = prov

    await set_cached(cache_key, response, request.app.state.cache)
    return response
