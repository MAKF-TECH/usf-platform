from __future__ import annotations

import uuid
from typing import Any

import httpx
from loguru import logger

from usf_api.config import settings


async def check_permission(
    user_id: str,
    tenant_id: str,
    role: str,
    action: str,
    resource: str,
    resource_attrs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Call OPA sidecar to evaluate ABAC policy.
    
    OPA input structure:
      {
        "input": {
          "user": {"id": ..., "tenant_id": ..., "role": ...},
          "action": "query" | "read" | "write",
          "resource": {"type": "metric", "name": ...},
          "context": ...
        }
      }
    
    Returns OPA result dict with "allow" (bool) and optional "filters" (list).
    """
    opa_input = {
        "input": {
            "user": {
                "id": user_id,
                "tenant_id": tenant_id,
                "role": role,
            },
            "action": action,
            "resource": {
                "type": resource,
                **(resource_attrs or {}),
            },
        }
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.opa_url}/v1/data/usf/authz",
                json=opa_input,
            )
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPError as exc:
        # Fail open in dev, fail closed in prod
        logger.error("OPA call failed — failing closed", error=str(exc))
        return {"allow": False, "filters": [], "error": str(exc)}

    result_data = result.get("result", {})
    allow = result_data.get("allow", False)
    filters = result_data.get("filters", [])

    logger.info(
        "ABAC decision",
        user_id=user_id,
        role=role,
        action=action,
        resource=resource,
        allow=allow,
        filters=filters,
    )

    return {"allow": allow, "filters": filters}
