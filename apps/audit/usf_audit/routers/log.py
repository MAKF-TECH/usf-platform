from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from usf_audit.db import get_session
from usf_audit.models import AuditAction, AuditLog, AuditLogRead, AuditStatus
from usf_audit.services.lineage_tracer import get_full_provenance_jsonld

router = APIRouter(prefix="/log", tags=["log"])


@router.get("", response_model=list[AuditLogRead])
async def list_logs(
    session: Annotated[AsyncSession, Depends(get_session)],
    tenant_id: str | None = None,
    user_id: str | None = None,
    context: str | None = None,
    action: AuditAction | None = None,
    status: AuditStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
) -> list[AuditLogRead]:
    stmt = select(AuditLog).order_by(col(AuditLog.created_at).desc())
    if tenant_id:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if context:
        stmt = stmt.where(AuditLog.context == context)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if status:
        stmt = stmt.where(AuditLog.status == status)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    result = await session.exec(stmt.offset(offset).limit(limit))
    return [AuditLogRead.model_validate(r) for r in result.all()]


@router.get("/{query_hash}")
async def get_log_by_query_hash(query_hash: str) -> dict:
    """Return full PROV-O JSON-LD for a query run."""
    try:
        return await get_full_provenance_jsonld(query_hash)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"QLever query failed: {exc}")
