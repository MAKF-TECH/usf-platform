from __future__ import annotations

"""IEC CIM (CGMES) RDF/XML parser → rdflib Graph → usf-kg."""

from pathlib import Path

import httpx
from loguru import logger
from rdflib import Graph

from usf_ingest.config import get_settings


def parse_cim_rdf(file_path: str | Path) -> Graph:
    g = Graph()
    g.parse(str(file_path), format="xml")
    logger.info(f"Parsed CIM RDF: {len(g)} triples from {file_path}")
    return g


def parse_cim_from_bytes(data: bytes, format: str = "xml") -> Graph:
    g = Graph()
    g.parse(data=data, format=format)
    logger.info(f"Parsed CIM from bytes: {len(g)} triples")
    return g


async def insert_cim_graph(graph: Graph, named_graph_uri: str) -> None:
    settings = get_settings()
    turtle = graph.serialize(format="turtle")
    sparql = f"INSERT DATA {{ GRAPH <{named_graph_uri}> {{ {turtle} }} }}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{settings.USF_KG_URL}/update", data=sparql, headers={"Content-Type": "application/sparql-update"})
        r.raise_for_status()
    logger.info("Inserted CIM triples", extra={"named_graph": named_graph_uri, "triples": len(graph)})
