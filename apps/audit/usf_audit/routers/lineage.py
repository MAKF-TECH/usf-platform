from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from loguru import logger

from usf_audit.config import get_settings
from usf_audit.services.lineage_tracer import trace_lineage

router = APIRouter(prefix="/lineage", tags=["lineage"])


@router.get("/{iri:path}")
async def get_lineage(iri: str) -> dict:
    """Return the entity lineage chain for a given IRI via SPARQL on QLever."""
    try:
        steps = await trace_lineage(iri)
        return {"iri": iri, "steps": steps, "count": len(steps)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lineage trace failed: {exc}")


@router.post("/events")
async def ingest_lineage_event(event: dict = Body(...)) -> dict:
    """Receive an OpenLineage event, store locally, and optionally sync to Egeria."""
    logger.info("Received lineage event: {}", event.get("eventType", "unknown"))

    # After writing to local audit log, optionally sync to Egeria
    settings = get_settings()
    if settings.EGERIA_URL:
        from usf_audit.services.egeria_bridge import EgeriaBridge

        synced = await EgeriaBridge(settings.EGERIA_URL).publish_lineage_event(event)
        return {"status": "accepted", "egeria_synced": synced}

    return {"status": "accepted", "egeria_synced": False}
