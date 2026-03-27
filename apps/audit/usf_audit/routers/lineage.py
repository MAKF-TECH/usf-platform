from __future__ import annotations

from fastapi import APIRouter, HTTPException
from usf_audit.services.lineage_tracer import trace_lineage

router = APIRouter(prefix="/lineage", tags=["lineage"])


@router.get("/{iri:path}")
async def get_lineage(iri: str) -> dict:
    try:
        steps = await trace_lineage(iri)
        return {"iri": iri, "steps": steps, "count": len(steps)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lineage trace failed: {exc}")
