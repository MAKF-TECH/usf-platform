from __future__ import annotations

"""SPARQL-based lineage tracer — traverses PROV-O chains in QLever."""

import httpx
from loguru import logger

from usf_audit.config import get_settings


LINEAGE_SPARQL_TEMPLATE = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX usf: <https://usf.platform/ontology/>

SELECT ?entity ?activity ?agent ?startTime ?endTime WHERE {{
  BIND(<{iri}> AS ?entity)
  ?activity prov:used ?entity ;
            prov:wasAssociatedWith ?agent ;
            prov:startedAtTime ?startTime ;
            prov:endedAtTime ?endTime .
  OPTIONAL {{ ?entity prov:wasDerivedFrom ?source }}
}}
LIMIT 100
"""


async def trace_lineage(iri: str) -> list[dict]:
    """
    Traverse PROV-O chains for a given entity IRI in QLever.

    Returns a list of lineage steps: [{entity, activity, agent, startTime, endTime}]
    """
    settings = get_settings()
    sparql = LINEAGE_SPARQL_TEMPLATE.format(iri=iri)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.QLEVER_URL}/sparql",
            params={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        data = response.json()

    bindings = data.get("results", {}).get("bindings", [])
    steps = [
        {k: v.get("value") for k, v in binding.items()}
        for binding in bindings
    ]
    logger.info(f"Lineage trace for {iri}: {len(steps)} steps")
    return steps


async def get_full_provenance_jsonld(query_hash: str) -> dict:
    """Fetch the full PROV-O JSON-LD document for a query run."""
    settings = get_settings()
    sparql = f"""
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX usf: <https://usf.platform/ontology/>

CONSTRUCT {{
  ?activity ?p ?o .
  ?entity ?ep ?eo .
}}
WHERE {{
  ?activity usf:queryHash "{query_hash}" ;
            ?p ?o .
  OPTIONAL {{
    ?entity prov:wasGeneratedBy ?activity ;
            ?ep ?eo .
  }}
}}
"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{settings.QLEVER_URL}/sparql",
            params={"query": sparql},
            headers={"Accept": "application/ld+json"},
        )
        response.raise_for_status()
        return response.json()
