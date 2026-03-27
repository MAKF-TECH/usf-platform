from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Annotated

from usf_audit.db import get_session
from usf_audit.models import AuditLog, AuditAction, AuditStatus

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    tenant_id: str | None = None,
) -> dict:
    """Audit statistics for the dashboard."""
    # Total query count
    count_stmt = select(func.count(AuditLog.id))
    if tenant_id:
        count_stmt = count_stmt.where(AuditLog.tenant_id == tenant_id)
    total = (await session.exec(count_stmt)).one()

    # By action
    by_action_stmt = select(AuditLog.action, func.count(AuditLog.id)).group_by(AuditLog.action)
    if tenant_id:
        by_action_stmt = by_action_stmt.where(AuditLog.tenant_id == tenant_id)
    by_action = dict((await session.exec(by_action_stmt)).all())

    # By status
    by_status_stmt = select(AuditLog.status, func.count(AuditLog.id)).group_by(AuditLog.status)
    if tenant_id:
        by_status_stmt = by_status_stmt.where(AuditLog.tenant_id == tenant_id)
    by_status = dict((await session.exec(by_status_stmt)).all())

    # Top users (up to 10)
    top_users_stmt = (
        select(AuditLog.user_id, func.count(AuditLog.id).label("count"))
        .group_by(AuditLog.user_id)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    )
    if tenant_id:
        top_users_stmt = top_users_stmt.where(AuditLog.tenant_id == tenant_id)
    top_users = [{"user_id": r[0], "count": r[1]} for r in (await session.exec(top_users_stmt)).all()]

    # Top contexts
    top_contexts_stmt = (
        select(AuditLog.context, func.count(AuditLog.id).label("count"))
        .where(AuditLog.context != None)
        .group_by(AuditLog.context)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    )
    if tenant_id:
        top_contexts_stmt = top_contexts_stmt.where(AuditLog.tenant_id == tenant_id)
    top_contexts = [{"context": r[0], "count": r[1]} for r in (await session.exec(top_contexts_stmt)).all()]

    return {
        "total": total,
        "by_action": by_action,
        "by_status": by_status,
        "top_users": top_users,
        "top_contexts": top_contexts,
        "tenant_id": tenant_id,
    }
