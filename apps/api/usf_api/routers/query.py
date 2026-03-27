from __future__ import annotations

import hashlib
import uuid
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
    """
    Main query endpoint:
    1. Extract context from header (or resolve/409 if ambiguous)
    2. ABAC check via OPA
    3. Check Valkey cache
    4. Forward to usf-query
    5. Wrap result in standard envelope + PROV-O
    """
    user_id = claims["sub"]
    tenant_id = claims["tenant_id"]
    role = claims["role"]
    query_id = str(uuid.uuid4())

    # Step 1: Resolve context
    context = await resolve_context(
        context_header=x_usf_context,
        tenant_id=tenant_id,
        metric_name=req.metric,
    )

    # Step 2: ABAC check
    abac_result = await check_permission(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        action="query",
        resource="metric",
        resource_attrs={"name": req.metric, "context": context},
    )
    if not abac_result.get("allow"):
        raise HTTPException(status_code=403, detail="Access denied by ABAC policy")

    abac_decision = "permit"

    # Step 3: Build query payload for usf-query
    query_payload: dict[str, Any] = {
        "context": context,
        "tenant_id": tenant_id,
    }
    if req.sparql:
        query_payload.update({"query": req.sparql, "query_type": "sparql"})
    elif req.sql:
        query_payload.update({"query": req.sql, "query_type": "sql"})
    elif req.question:
        # NL query
        pass
    elif req.metric:
        # Compile metric to SQL
        pass

    # Apply ABAC row-level filters
    if abac_result.get("filters"):
        if "filters" not in query_payload:
            query_payload["filters"] = {}
        query_payload["filters"].update({"_abac_filter": abac_result["filters"]})

    query_hash = hashlib.sha256(str(query_payload).encode()).hexdigest()[:16]

    # Step 4: Check cache
    cache_key = make_query_cache_key(tenant_id, context, query_hash)
    cached = await get_cached(cache_key, request.app.state.cache)
    if cached:
        logger.info("Serving from cache", cache_key=cache_key, query_id=query_id)
        return cached

    # Step 5: Forward to usf-query
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if req.question:
                # NL query endpoint
                resp = await client.post(
                    f"{settings.usf_query_url}/execute/nl",
                    json={
                        "question": req.question,
                        "context": context,
                        "tenant_id": tenant_id,
                        "ontology_context": "",  # TODO: fetch from KG
                        "max_results": req.max_results,
                    },
                )
            elif req.sparql:
                resp = await client.post(
                    f"{settings.usf_query_url}/execute/sparql",
                    json=query_payload,
                )
            elif req.sql:
                resp = await client.post(
                    f"{settings.usf_query_url}/execute/sql",
                    json=query_payload,
                )
            elif req.metric:
                compile_resp = await client.post(
                    f"{settings.usf_query_url}/compile/",
                    json={
                        "metric_name": req.metric,
                        "context": context,
                        "tenant_id": tenant_id,
                        "dialect": "postgres",
                    },
                )
                compile_resp.raise_for_status()
                compiled = compile_resp.json()
                resp = await client.post(
                    f"{settings.usf_query_url}/execute/sql",
                    json={"query": compiled["sql"], "query_type": "sql", "context": context},
                )
            else:
                raise HTTPException(status_code=422, detail="Provide question, sparql, sql, or metric")

            resp.raise_for_status()
            query_result = resp.json()
    except httpx.HTTPError as exc:
        logger.error("usf-query request failed", error=str(exc), query_id=query_id)
        raise HTTPException(status_code=502, detail=f"Query service error: {exc}")

    # Step 6: Build PROV-O
    backend = query_result.get("backend_used")
    prov_block = build_prov_o(
        query_id=query_id,
        user_id=user_id,
        tenant_id=tenant_id,
        context=context,
        query_hash=query_hash,
        abac_decision=abac_decision,
        backend=backend,
    )

    response = wrap(
        data=query_result,
        provenance=None,
    )
    response["provenance"] = prov_block

    # Cache the result
    await set_cached(cache_key, response, request.app.state.cache)

    return response
