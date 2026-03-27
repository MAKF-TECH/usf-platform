from __future__ import annotations

"""JSON-LD parser.

Parses JSON-LD documents → rdflib Graph → schema alignment → usf-kg.
"""

import json
from pathlib import Path
from typing import Any

import httpx
from loguru import logger
from rdflib import Graph

from usf_ingest.config import get_settings
from usf_ingest.pipelines.semi_structured.schema_aligner import align_graph


def parse_jsonld(source: str | dict | Path) -> Graph:
    """Parse JSON-LD into rdflib Graph."""
    g = Graph()
    if isinstance(source, Path):
        g.parse(str(source), format="json-ld")
    elif isinstance(source, dict):
        g.parse(data=json.dumps(source), format="json-ld")
    else:
        # Try as file path first, then as string data
        try:
            g.parse(source, format="json-ld")
        except Exception:
            g.parse(data=source, format="json-ld")
    logger.info(f"Parsed JSON-LD: {len(g)} triples")
    return g


async def ingest_jsonld(
    source: str | dict | Path,
    named_graph_uri: str,
    tenant_id: str,
    align: bool = True,
) -> dict:
    """Full pipeline: parse → optional align → insert to KG."""
    graph = parse_jsonld(source)
    stats = {"raw_triples": len(graph), "aligned": False, "quarantined": 0}

    if align:
        aligned_graph, quarantined = await align_graph(graph, tenant_id=tenant_id)
        stats["aligned"] = True
        stats["quarantined"] = quarantined
        graph = aligned_graph

    await _insert_to_kg(graph, named_graph_uri)
    stats["inserted_triples"] = len(graph)
    return stats


async def _insert_to_kg(graph: Graph, named_graph_uri: str) -> None:
    settings = get_settings()
    turtle = graph.serialize(format="turtle")
    sparql_update = f"""
INSERT DATA {{
  GRAPH <{named_graph_uri}> {{
    {turtle}
  }}
}}
"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.USF_KG_URL}/update",
            data=sparql_update,
            headers={"Content-Type": "application/sparql-update"},
        )
        response.raise_for_status()
    logger.info(
        "Inserted JSON-LD triples into KG",
        extra={"named_graph": named_graph_uri, "triples": len(graph)},
    )
