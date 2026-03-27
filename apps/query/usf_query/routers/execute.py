from __future__ import annotations

from fastapi import APIRouter, HTTPException, Body

from usf_query.models import (
    NLQueryRequest,
    OGRagRequest,
    QueryResult,
    QueryType,
    SemanticQuery,
)
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
    """Execute raw SQL via Wren Engine semantic layer."""
    req.query_type = QueryType.SQL
    return await route_query(req)


@router.post("/sparql", response_model=QueryResult)
async def execute_sparql(req: SPARQLRequest) -> QueryResult:
    """Execute SPARQL — routed to QLever, Ontop, or ArcadeDB based on query pattern."""
    req.query_type = QueryType.SPARQL
    return await route_query(req)


@router.post("/nl", response_model=QueryResult)
async def execute_nl(req: NLQueryRequest) -> QueryResult:
    """NL → SPARQL pipeline: LLM generates SPARQL, validates against OWL, executes."""
    if not req.ontology_context:
        raise HTTPException(
            status_code=422,
            detail="ontology_context is required for NL queries. Provide the OWL/Turtle schema.",
        )
    return await execute_nl_query(
        question=req.question,
        ontology_context=req.ontology_context,
        context=req.context,
        tenant_id=req.tenant_id,
    )


@router.post("/ograg", response_model=list)
async def execute_ograg(req: OGRagRequest) -> list:
    """
    OG-RAG: ontology-grounded retrieval from knowledge graph.
    Returns top-k hyperedges as structured LLM context.
    """
    kg_client = get_arcadedb()
    hyperedges = await ograg_retrieve(
        question=req.question,
        context=req.context or "default",
        kg_client=kg_client,
        k=req.k,
        max_depth=req.max_depth,
    )
    return [he.model_dump() for he in hyperedges]
