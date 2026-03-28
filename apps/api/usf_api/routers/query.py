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


@router.post(
    "/",
    summary="Execute a semantic query",
    description="""
Execute a governed semantic query against the USF knowledge graph.

**Query Modes:** Provide one of `question` (NL), `sparql`, `sql`, or `metric`.

**Context Resolution:**
- If `X-USF-Context` header is set → query scoped to that context's named graph
- If omitted and metric has ONE context → auto-resolves
- If omitted and metric has MULTIPLE contexts → returns **409 Conflict** with available options

**ABAC:** Every query is checked against OPA policies before execution.
Row-level filtering and PII masking are applied automatically.

**PROV-O:** Response includes W3C PROV-O JSON-LD provenance block.

**Caching:** Results are cached in Valkey (L2). Cache hits skip query execution.
    """,
    responses={
        200: {"description": "Query executed successfully with provenance"},
        403: {"description": "ABAC denied — insufficient role/clearance"},
        409: {"description": "Context ambiguous — metric defined in multiple contexts"},
        422: {"description": "Invalid query parameters — must provide question, sparql, sql, or metric"},
        502: {"description": "Upstream query service error"},
    },
    tags=["query"],
)
async def run_query(
    req: QueryRequest,
    request: Request,
    claims: Annotated[dict, Depends(get_current_user)],
    x_usf_context: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """
    Main query endpoint:
    1. Extract / resolve context (or 409 if ambiguous)
    2. ABAC check via OPA
    3. Check Valkey L2 cache
    4. Forward to usf-query service if cache miss
    5. Wrap result in standard envelope + PROV-O
    6. Write to Valkey cache
    7. Write audit log entry
    """
    user_id_str = claims["sub"]
    tenant_id_str = claims["tenant_id"]
    user_id = uuid.UUID(user_id_str)
    tenant_id = uuid.UUID(tenant_id_str)
    role = claims["role"]
    query_id = str(uuid.uuid4())
    started_at = _utcnow()

    # Step 1: Resolve context
    request.state.metric = req.metric
    ctx_res: ContextResolution = await resolve_context(
        context_header=x_usf_context,
        tenant_id=tenant_id_str,
        metric_name=req.metric,
    )
    context = ctx_res.context

    # Step 2: ABAC check via OPA
    user_claims = TokenClaims(
        sub=user_id_str,
        tenant_id=tenant_id_str,
        role=role,
        department=claims.get("department"),
        clearance=claims.get("clearance", "internal"),
        email=claims.get("email"),
    )
    resource = ResourceRequest(context=context, metric=req.metric, action="read")
    abac: ABACDecision = await check_abac(user_claims, resource)

    if not abac.allow:
        await _write_audit(
            request=request, user_id=user_id, tenant_id=tenant_id,
            query_hash="", context=context, metric=req.metric,
            backend=None, abac_decision="deny", cache_hit=False,
            execution_ms=None, error="ABAC denied",
        )
        raise HTTPException(status_code=403, detail="Access denied by ABAC policy")

    # Step 3: Build query payload
    query_payload: dict[str, Any] = {"context": context, "tenant_id": tenant_id_str}
    if req.sparql:
        query_payload.update({"query": req.sparql, "query_type": "sparql"})
    elif req.sql:
        query_payload.update({"query": req.sql, "query_type": "sql"})
    elif req.question:
        query_payload.update({
            "question": req.question,
            "ontology_context": "",
            "max_results": req.max_results,
        })
    elif req.metric:
        query_payload.update({
            "metric": req.metric,
            "dimensions": req.dimensions,
            "filters": req.filters,
            "time_range": req.time_range,
        })

    if abac.row_filters:
        query_payload.setdefault("filters", {})
        query_payload["filters"]["_abac"] = abac.row_filters

    query_hash = hashlib.sha256(str(query_payload).encode()).hexdigest()[:16]

    # Step 4: Check Valkey L2 cache
    cache_key = make_query_cache_key(tenant_id_str, context, query_hash)
    cached = await get_cached(cache_key, request.app.state.cache)
    if cached:
        logger.info("Cache HIT", cache_key=cache_key)
        ended_at = _utcnow()
        await _write_audit(
            request=request, user_id=user_id, tenant_id=tenant_id,
            query_hash=query_hash, context=context, metric=req.metric,
            backend=cached.get("data", {}).get("backend_used"),
            abac_decision="permit", cache_hit=True,
            execution_ms=(ended_at - started_at).total_seconds() * 1000,
        )
        return cached

    # Step 5: Forward to usf-query service
    query_result: dict[str, Any] = {}
    backend_used: str | None = None

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if req.question:
                resp = await client.post(
                    f"{settings.usf_query_url}/execute/nl",
                    json={
                        "question": req.question,
                        "context": context,
                        "tenant_id": tenant_id_str,
                        "ontology_context": "",
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
                        "tenant_id": tenant_id_str,
                        "dimensions": req.dimensions,
                        "filters": req.filters,
                        "time_range": req.time_range,
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
            backend_used = query_result.get("backend_used")

    except httpx.HTTPError as exc:
        ended_at = _utcnow()
        logger.error("usf-query request failed", error=str(exc), query_id=query_id)
        await _write_audit(
            request=request, user_id=user_id, tenant_id=tenant_id,
            query_hash=query_hash, context=context, metric=req.metric,
            backend=None, abac_decision="permit", cache_hit=False,
            execution_ms=(ended_at - started_at).total_seconds() * 1000,
            error=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"Query service error: {exc}")

    ended_at = _utcnow()

    # PII field masking
    if abac.pii_fields and isinstance(query_result.get("rows"), list):
        for row in query_result["rows"]:
            for field in abac.pii_fields:
                if field in row:
                    row[field] = "***"

    # Step 6: Build PROV-O and wrap response
    prov_block = build_prov_o(
        query_id=query_id,
        user_id=user_id_str,
        tenant_id=tenant_id_str,
        context=context,
        query_hash=query_hash,
        abac_decision="permit",
        backend=backend_used,
    )
    response = wrap(data=query_result)
    response["provenance"] = prov_block

    # Step 7: Write to cache + audit log
    await set_cached(cache_key, response, request.app.state.cache)
    await _write_audit(
        request=request, user_id=user_id, tenant_id=tenant_id,
        query_hash=query_hash, context=context, metric=req.metric,
        backend=backend_used, abac_decision="permit", cache_hit=False,
        execution_ms=(ended_at - started_at).total_seconds() * 1000,
    )

    return response
