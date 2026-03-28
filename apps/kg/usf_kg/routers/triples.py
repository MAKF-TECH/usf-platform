"""POST /triples — bulk insert triples into a named graph."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from rdflib import URIRef, Literal

from usf_rdf.triples import Triple
from ..models import BulkInsertRequest, BulkInsertResponse

router = APIRouter(prefix="/triples", tags=["triples"])


def _parse_node(value: str):
    if value.startswith("http://") or value.startswith("https://") or value.startswith("usf://"):
        return URIRef(value)
    return Literal(value)


@router.post(
    "",
    response_model=BulkInsertResponse,
    status_code=201,
    summary="Bulk insert triples",
    description="Insert a batch of RDF triples into the specified named graph via QLever SPARQL UPDATE. Subjects and predicates must be valid IRIs. Objects can be IRIs or literals.",
    responses={
        201: {"description": "Triples inserted successfully"},
        502: {"description": "QLever insert failed"},
    },
    tags=["triples"],
)
async def bulk_insert(request: Request, body: BulkInsertRequest):
    """Insert a batch of triples into the specified named graph."""
    qlever = request.app.state.qlever
    triples = [
        Triple(
            subject=URIRef(t.subject),
            predicate=URIRef(t.predicate),
            obj=_parse_node(t.object),
        )
        for t in body.triples
    ]
    try:
        inserted = await qlever.insert_triples(body.graph_uri, triples)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"QLever insert failed: {exc}") from exc

    return BulkInsertResponse(graph_uri=body.graph_uri, inserted=inserted)
