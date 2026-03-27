from __future__ import annotations

"""IEC CIM (CGMES) RDF/XML parser.

Parses CIM RDF/XML → rdflib Graph → inserts to usf-kg.
"""

from pathlib import Path

import httpx
from loguru import logger
from rdflib import Graph

from usf_ingest.config import get_settings


def parse_cim_rdf(file_path: str | Path) -> Graph:
    """Parse an IEC CIM RDF/XML (CGMES) file and return an rdflib Graph."""
    g = Graph()
    g.parse(str(file_path), format="xml")
    logger.info(f"Parsed CIM RDF: {len(g)} triples from {file_path}")
    return g


def parse_cim_from_bytes(data: bytes, format: str = "xml") -> Graph:
    """Parse CIM RDF from raw bytes."""
    g = Graph()
    g.parse(data=data, format=format)
    logger.info(f"Parsed CIM from bytes: {len(g)} triples")
    return g


async def insert_cim_graph(
    graph: Graph,
    named_graph_uri: str,
) -> None:
    """Insert CIM graph into the USF KG via SPARQL UPDATE."""
    settings = get_settings()
    turtle = graph.serialize(format="turtle")
    sparql_update = f"""
INSERT DATA {{
  GRAPH <{named_graph_uri}> {{
    {turtle}
  }}
}}
"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.USF_KG_URL}/update",
            data=sparql_update,
            headers={"Content-Type": "application/sparql-update"},
        )
        response.raise_for_status()
    logger.info(
        "Inserted CIM triples into KG",
        extra={"named_graph": named_graph_uri, "triples": len(graph)},
    )
