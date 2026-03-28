"""GET /entities/{iri}, POST /entities/resolve, POST /entities/resolve-by-label."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from urllib.parse import unquote

from ..models import EntityDetail, EntityProperty, EntityResolveRequest, EntityResolveResponse

router = APIRouter(prefix="/entities", tags=["entities"])


# ── Label-based resolution models ────────────────────────────────────────────

class ResolveLabelRequest(BaseModel):
    candidate_label: str = Field(..., description="Raw entity label to resolve")
    ontology_class: str = Field(..., description="OWL class IRI for this entity type")
    tenant_id: str = Field(..., description="Tenant identifier")
    embedding: list[float] | None = Field(
        default=None,
        description="Optional sentence embedding for vector search (threshold 0.85)",
    )


class ResolveLabelResponse(BaseModel):
    canonical_iri: str
    is_new: bool
    confidence: float
    same_as_iri: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{entity_iri:path}", response_model=EntityDetail)
async def get_entity(entity_iri: str, request: Request):
    iri = unquote(entity_iri)
    qlever = request.app.state.qlever
    try:
        data = await qlever.entity_detail(iri)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not data["properties"] and not data["types"]:
        raise HTTPException(status_code=404, detail=f"Entity not found: {iri}")

    properties = [
        EntityProperty(
            predicate=row.get("p", ""),
            value=row.get("o", ""),
            source_graph=row.get("g"),
        )
        for row in data["properties"]
    ]
    return EntityDetail(iri=iri, types=data["types"], properties=properties)


@router.post("/resolve", response_model=EntityResolveResponse, status_code=200)
async def resolve_entity(request: Request, body: EntityResolveRequest):
    """Resolve multiple candidate IRIs to a canonical IRI via levenshtein / owl:sameAs."""
    resolver = request.app.state.entity_resolver
    try:
        result = await resolver.resolve(body.candidate_iris, strategy=body.strategy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return EntityResolveResponse(**result)


@router.post("/resolve-by-label", response_model=ResolveLabelResponse, status_code=200)
async def resolve_entity_by_label(request: Request, body: ResolveLabelRequest):
    """
    Resolve a raw entity label to a canonical IRI.
    Steps:
    1. Exact IRI lookup in ArcadeDB
    2. Vector similarity search (if embedding provided, threshold 0.85)
    3. Mint new IRI if no match: usf://{tenant}/entity/{class}/{sha256(label)[:8]}
    Writes owl:sameAs to QLever provenance graph when a match is found.
    """
    resolver = request.app.state.entity_resolver
    try:
        result = await resolver.resolve_entity(
            candidate_label=body.candidate_label,
            ontology_class=body.ontology_class,
            tenant_id=body.tenant_id,
            embedding=body.embedding,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ResolveLabelResponse(
        canonical_iri=result.canonical_iri,
        is_new=result.is_new,
        confidence=result.confidence,
        same_as_iri=result.same_as_iri,
    )
