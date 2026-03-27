from __future__ import annotations

"""Ontop loader — push R2RML mappings and trigger VKG refresh."""

import httpx
from loguru import logger

from usf_ingest.config import get_settings


async def upload_r2rml_mapping(mapping_turtle: str, mapping_name: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.put(
            f"{settings.ONTOP_URL}/ontop/v1/mapping",
            content=mapping_turtle.encode(),
            headers={"Content-Type": "text/turtle", "X-Mapping-Name": mapping_name},
        )
        r.raise_for_status()
    logger.info("Uploaded R2RML to Ontop", extra={"mapping_name": mapping_name})
    return r.json()


async def trigger_vkg_refresh(mapping_name: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{settings.ONTOP_URL}/ontop/v1/mapping/{mapping_name}/refresh")
        r.raise_for_status()
    logger.info("Triggered Ontop VKG refresh", extra={"mapping_name": mapping_name})
    return r.json()


async def query_vkg(sparql: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(f"{settings.ONTOP_URL}/sparql", params={"query": sparql}, headers={"Accept": "application/sparql-results+json"})
        r.raise_for_status()
        return r.json()
