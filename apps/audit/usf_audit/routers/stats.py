from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from usf_audit.db import get_session
from usf_audit.models import AuditLog

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    tenant_id: str | None = None,
) -> dict:
    def _add_filter(stmt, model=AuditLog):
        return stmt.where(AuditLog.tenant_id == tenant_id) if tenant_id else stmt

    total = (await session.exec(_add_filter(select(func.count(AuditLog.id))))).one()

    by_action = dict((await session.exec(_add_filter(select(AuditLog.action, func.count(AuditLog.id)).group_by(AuditLog.action)))).all())

    by_status = dict((await session.exec(_add_filter(select(AuditLog.status, func.count(AuditLog.id)).group_by(AuditLog.status)))).all())

    top_users = [
        {"user_id": r[0], "count": r[1]}
        for r in (await session.exec(_add_filter(
            select(AuditLog.user_id, func.count(AuditLog.id).label("c"))
            .group_by(AuditLog.user_id).order_by(func.count(AuditLog.id).desc()).limit(10)
        ))).all()
    ]

    top_contexts = [
        {"context": r[0], "count": r[1]}
        for r in (await session.exec(_add_filter(
            select(AuditLog.context, func.count(AuditLog.id).label("c"))
            .where(AuditLog.context.isnot(None))
            .group_by(AuditLog.context).order_by(func.count(AuditLog.id).desc()).limit(10)
        ))).all()
    ]

    return {
        "total": total,
        "by_action": by_action,
        "by_status": by_status,
        "top_users": top_users,
        "top_contexts": top_contexts,
        "tenant_id": tenant_id,
    }
