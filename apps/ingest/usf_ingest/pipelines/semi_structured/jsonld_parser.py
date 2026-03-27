from __future__ import annotations

"""JSON-LD parser → rdflib Graph → optional schema alignment → usf-kg."""

import json
from pathlib import Path

import httpx
from loguru import logger
from rdflib import Graph

from usf_ingest.config import get_settings
from usf_ingest.pipelines.semi_structured.schema_aligner import align_graph


def parse_jsonld(source: str | dict | Path) -> Graph:
    g = Graph()
    if isinstance(source, Path):
        g.parse(str(source), format="json-ld")
    elif isinstance(source, dict):
        g.parse(data=json.dumps(source), format="json-ld")
    else:
        try:
            g.parse(source, format="json-ld")
        except Exception:
            g.parse(data=source, format="json-ld")
    logger.info(f"Parsed JSON-LD: {len(g)} triples")
    return g


async def ingest_jsonld(source: str | dict | Path, named_graph_uri: str, tenant_id: str, align: bool = True) -> dict:
    graph = parse_jsonld(source)
    stats: dict = {"raw_triples": len(graph), "aligned": False, "quarantined": 0}

    if align:
        graph, quarantined = await align_graph(graph, tenant_id=tenant_id)
        stats["aligned"] = True
        stats["quarantined"] = quarantined

    settings = get_settings()
    turtle = graph.serialize(format="turtle")
    sparql = f"INSERT DATA {{ GRAPH <{named_graph_uri}> {{ {turtle} }} }}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{settings.USF_KG_URL}/update", data=sparql, headers={"Content-Type": "application/sparql-update"})
        r.raise_for_status()

    stats["inserted_triples"] = len(graph)
    logger.info("Ingested JSON-LD", extra={"named_graph": named_graph_uri, **stats})
    return stats
