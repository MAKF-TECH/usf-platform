from __future__ import annotations
from typing import Any
import httpx
from loguru import logger
from usf_api.config import settings


async def check_permission(user_id: str, tenant_id: str, role: str, action: str,
                            resource: str, resource_attrs: dict[str, Any] | None = None) -> dict[str, Any]:
    opa_input = {"input": {"user": {"id": user_id, "tenant_id": tenant_id, "role": role},
                            "action": action, "resource": {"type": resource, **(resource_attrs or {})}}}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{settings.opa_url}/v1/data/usf/authz", json=opa_input)
            resp.raise_for_status()
            result = resp.json().get("result", {})
    except httpx.HTTPError as exc:
        logger.error("OPA call failed — denying", error=str(exc))
        return {"allow": False, "filters": []}
    allow = result.get("allow", False)
    filters = result.get("filters", [])
    logger.info("ABAC decision", user_id=user_id, action=action, resource=resource, allow=allow)
    return {"allow": allow, "filters": filters}
