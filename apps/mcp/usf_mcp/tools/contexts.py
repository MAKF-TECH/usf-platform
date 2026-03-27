from __future__ import annotations

from typing import Any

from loguru import logger

from usf_mcp.client import get_client


async def list_contexts() -> list[dict[str, Any]]:
    """
    List all available semantic contexts for the current tenant.
    
    Contexts define different views of the same data:
    - 'risk': Financial risk exposure view
    - 'finance': Accounting/settlements view
    - 'ops': Operational data view
    
    Returns: List of context descriptors with name, description, and metric count.
    """
    client = get_client()
    result = await client.list_contexts()
    contexts = result.get("data", {}).get("contexts", result.get("data", []))
    logger.info("MCP list_contexts", count=len(contexts))
    return contexts
