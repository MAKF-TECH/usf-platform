from __future__ import annotations
from typing import Any
from loguru import logger
from usf_mcp.client import get_client


async def search_entities(query: str, entity_type: str | None = None, context: str | None = None) -> list[dict[str, Any]]:
    data = await get_client().search_entities(query=query, entity_type=entity_type, context=context)
    return data.get("data", {}).get("entities", data.get("data", []))


async def get_entity(iri: str) -> dict[str, Any]:
    data = await get_client().get_entity(iri)
    return data.get("data", data)
