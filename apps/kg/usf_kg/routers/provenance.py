"""GET /provenance/{iri} — PROV-O chain for an entity."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from urllib.parse import unquote

from ..models import ProvenanceResponse
from usf_rdf import ProvOBuilder

router = APIRouter(prefix="/provenance", tags=["provenance"])
_prov_builder = ProvOBuilder()


@router.get("/{entity_iri:path}", response_model=ProvenanceResponse)
async def get_provenance(entity_iri: str, request: Request):
    iri = unquote(entity_iri)
    qlever = request.app.state.qlever

    try:
        chain = await qlever.provenance_chain(iri)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not chain:
        raise HTTPException(status_code=404, detail=f"No provenance found for: {iri}")

    # Build a PROV-O JSON-LD document from the chain
    derivation_iris = [row.get("source", "") for row in chain if row.get("source")]
    activity_iri = chain[0].get("activity") if chain else None

    prov_o = _prov_builder.entity_derivation(
        entity_iri=iri,
        derived_from_iris=list(set(derivation_iris)),
        activity_iri=activity_iri,
    )
    # Enrich with activities
    prov_o["usf:activities"] = chain

    return ProvenanceResponse(entity_iri=iri, prov_o=prov_o)
