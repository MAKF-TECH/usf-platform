from __future__ import annotations

from fastapi import APIRouter, HTTPException
from loguru import logger

from usf_audit.config import get_settings
from usf_audit.models import ExportRequest

import httpx

router = APIRouter(prefix="/export", tags=["export"])


@router.post("", status_code=200)
async def export_provenance(payload: ExportRequest) -> dict:
    """
    SPARQL dump of PROV-O graph for a tenant/time window.
    Returns Turtle or JSON-LD.
    """
    settings = get_settings()
    accept_header = "application/ld+json" if payload.format == "jsonld" else "text/turtle"

    sparql = f"""
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX usf: <https://usf.platform/ontology/>

CONSTRUCT {{
  ?activity ?p ?o .
}}
WHERE {{
  ?activity a prov:Activity ;
            usf:tenantId "{payload.tenant_id}" ;
            prov:startedAtTime ?t ;
            ?p ?o .
  FILTER(?t >= "{payload.start.isoformat()}"^^xsd:dateTime &&
         ?t <= "{payload.end.isoformat()}"^^xsd:dateTime)
}}
"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{settings.QLEVER_URL}/sparql",
                params={"query": sparql},
                headers={"Accept": accept_header},
            )
            response.raise_for_status()
            content = response.text
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"QLever export failed: {exc}")

    return {
        "tenant_id": payload.tenant_id,
        "format": payload.format,
        "content": content,
    }
