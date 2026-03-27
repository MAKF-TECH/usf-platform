from __future__ import annotations
from fastapi import APIRouter, HTTPException
from usf_query.models import NLQueryRequest, OGRagRequest, QueryResult, QueryType, SemanticQuery
from usf_query.services.nl2sparql import execute_nl_query
from usf_query.services.ograg import ograg_retrieve
from usf_query.services.query_router import route_query, get_arcadedb

router = APIRouter(prefix="/execute", tags=["execute"])


class SQLRequest(SemanticQuery):
    query_type: QueryType = QueryType.SQL


class SPARQLRequest(SemanticQuery):
    query_type: QueryType = QueryType.SPARQL


@router.post("/sql", response_model=QueryResult)
async def execute_sql(req: SQLRequest) -> QueryResult:
    req.query_type = QueryType.SQL
    return await route_query(req)


@router.post("/sparql", response_model=QueryResult)
async def execute_sparql(req: SPARQLRequest) -> QueryResult:
    req.query_type = QueryType.SPARQL
    return await route_query(req)


@router.post("/nl", response_model=QueryResult)
async def execute_nl(req: NLQueryRequest) -> QueryResult:
    if not req.ontology_context:
        raise HTTPException(status_code=422, detail="ontology_context is required for NL queries")
    return await execute_nl_query(req.question, req.ontology_context, req.context, req.tenant_id)


@router.post("/ograg")
async def execute_ograg(req: OGRagRequest) -> list:
    kg = get_arcadedb()
    edges = await ograg_retrieve(question=req.question, context=req.context or "default",
                                  kg_client=kg, k=req.k, max_depth=req.max_depth)
    return [e.model_dump() for e in edges]
