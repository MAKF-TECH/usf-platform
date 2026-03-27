"""GET /entities/{iri}, POST /entities/resolve."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from urllib.parse import unquote

from ..models import EntityDetail, EntityProperty, EntityResolveRequest, EntityResolveResponse

router = APIRouter(prefix="/entities", tags=["entities"])


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
    resolver = request.app.state.entity_resolver
    try:
        result = await resolver.resolve(body.candidate_iris, strategy=body.strategy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return EntityResolveResponse(**result)
