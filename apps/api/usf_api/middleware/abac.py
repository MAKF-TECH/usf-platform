from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel

from usf_api.config import settings


# ── Typed models ─────────────────────────────────────────────────────────────

class TokenClaims(BaseModel):
    """Decoded JWT claims for a user."""
    sub: str  # user_id
    tenant_id: str
    role: str
    department: str | None = None
    clearance: str = "internal"
    email: str | None = None

    @property
    def user_id(self) -> str:
        return self.sub


class ResourceRequest(BaseModel):
    """The resource being accessed."""
    context: str
    metric: str | None = None
    action: str = "read"


class ABACDecision(BaseModel):
    """Result from OPA ABAC policy evaluation."""
    allow: bool
    pii_fields: list[str] = []
    row_filters: list[Any] = []
    policy_version: str = "unknown"
    reason: str | None = None


# ── OPA client ───────────────────────────────────────────────────────────────

async def check_abac(user: TokenClaims, resource: ResourceRequest) -> ABACDecision:
    """
    Evaluate ABAC policy via OPA sidecar.

    OPA input schema:
      input.subject.{role, department, clearance, tenant_id}
      input.resource.{context, metric, action}
      input.environment.{timestamp}
    """
    payload = {
        "input": {
            "subject": {
                "role": user.role,
                "department": user.department,
                "clearance": user.clearance,
                "tenant_id": user.tenant_id,
                "user_id": user.user_id,
            },
            "resource": {
                "context": resource.context,
                "metric": resource.metric,
                "action": resource.action,
            },
            "environment": {
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        }
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.opa_url}/v1/data/usf/authz",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("OPA call failed — failing closed", error=str(exc))
        return ABACDecision(allow=False, reason=f"OPA unreachable: {exc}")

    result = data.get("result", {})
    allow = bool(result.get("allow", False))
    pii_fields = result.get("pii_fields", [])
    row_filters = result.get("filters", [])
    policy_version = result.get("policy_version", "unknown")

    logger.info(
        "ABAC decision",
        user_id=user.user_id,
        role=user.role,
        context=resource.context,
        metric=resource.metric,
        allow=allow,
        pii_fields=pii_fields,
    )

    return ABACDecision(
        allow=allow,
        pii_fields=pii_fields,
        row_filters=row_filters,
        policy_version=policy_version,
    )


async def check_permission(
    user_id: str,
    tenant_id: str,
    role: str,
    action: str,
    resource: str,
    resource_attrs: dict[str, Any] | None = None,
    department: str | None = None,
    clearance: str = "internal",
) -> dict[str, Any]:
    """
    Legacy compatibility wrapper — same interface as original check_permission.
    Returns {"allow": bool, "filters": list}.
    """
    user = TokenClaims(
        sub=user_id,
        tenant_id=tenant_id,
        role=role,
        department=department,
        clearance=clearance,
    )
    res = ResourceRequest(
        context=(resource_attrs or {}).get("context", "default"),
        metric=(resource_attrs or {}).get("name"),
        action=action,
    )
    decision = await check_abac(user, res)
    return {
        "allow": decision.allow,
        "filters": decision.row_filters,
        "pii_fields": decision.pii_fields,
    }
