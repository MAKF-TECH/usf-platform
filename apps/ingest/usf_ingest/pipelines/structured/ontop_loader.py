from __future__ import annotations

"""Ontop loader — push R2RML mappings to the Ontop sidecar and trigger VKG bootstrap."""

import httpx
from loguru import logger

from usf_ingest.config import get_settings


async def upload_r2rml_mapping(
    mapping_turtle: str,
    mapping_name: str,
) -> dict:
    """Upload R2RML mapping to Ontop REST API and return the response."""
    settings = get_settings()
    url = f"{settings.ONTOP_URL}/ontop/v1/mapping"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(
            url,
            content=mapping_turtle.encode(),
            headers={
                "Content-Type": "text/turtle",
                "X-Mapping-Name": mapping_name,
            },
        )
        response.raise_for_status()
        body = response.json()
        logger.info(
            "Uploaded R2RML mapping to Ontop",
            extra={"mapping_name": mapping_name, "status": response.status_code},
        )
        return body


async def trigger_vkg_refresh(mapping_name: str) -> dict:
    """Tell Ontop to reload its virtual KG from the stored R2RML mappings."""
    settings = get_settings()
    url = f"{settings.ONTOP_URL}/ontop/v1/mapping/{mapping_name}/refresh"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url)
        response.raise_for_status()
        body = response.json()
        logger.info("Triggered Ontop VKG refresh", extra={"mapping_name": mapping_name})
        return body


async def query_vkg(sparql: str) -> dict:
    """Execute a SPARQL SELECT query against Ontop's virtual KG endpoint."""
    settings = get_settings()
    url = f"{settings.ONTOP_URL}/sparql"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            url,
            params={"query": sparql},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()
        return response.json()
