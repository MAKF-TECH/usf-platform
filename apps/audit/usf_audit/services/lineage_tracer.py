from __future__ import annotations

"""SPARQL traversal of PROV-O chains in QLever."""

import httpx
from loguru import logger
from usf_audit.config import get_settings

LINEAGE_QUERY = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX usf: <https://usf.platform/ontology/>

SELECT ?entity ?activity ?agent ?startTime ?endTime WHERE {{
  BIND(<{iri}> AS ?entity)
  ?activity prov:used ?entity ;
            prov:wasAssociatedWith ?agent ;
            prov:startedAtTime ?startTime ;
            prov:endedAtTime ?endTime .
}}
LIMIT 100
"""


async def trace_lineage(iri: str) -> list[dict]:
    settings = get_settings()
    sparql = LINEAGE_QUERY.format(iri=iri)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{settings.QLEVER_URL}/sparql", params={"query": sparql}, headers={"Accept": "application/sparql-results+json"})
        r.raise_for_status()
    bindings = r.json().get("results", {}).get("bindings", [])
    steps = [{k: v.get("value") for k, v in b.items()} for b in bindings]
    logger.info(f"Lineage trace: {len(steps)} steps for {iri}")
    return steps


async def get_full_provenance_jsonld(query_hash: str) -> dict:
    settings = get_settings()
    sparql = f"""
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX usf: <https://usf.platform/ontology/>
CONSTRUCT {{ ?activity ?p ?o . }}
WHERE {{ ?activity usf:queryHash "{query_hash}" ; ?p ?o . }}
"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{settings.QLEVER_URL}/sparql", params={"query": sparql}, headers={"Accept": "application/ld+json"})
        r.raise_for_status()
        return r.json()
