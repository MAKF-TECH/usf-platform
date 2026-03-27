from __future__ import annotations
from typing import Any
from usf_mcp.client import get_client


async def list_contexts() -> list[dict[str, Any]]:
    data = await get_client().list_contexts()
    return data.get("data", {}).get("contexts", data.get("data", []))
