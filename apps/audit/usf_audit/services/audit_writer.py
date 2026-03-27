from __future__ import annotations

"""Append-only AuditLog writer — enforced by PostgreSQL RLS.

The application user has INSERT only on audit_log; no UPDATE/DELETE allowed.
This is enforced at the DB level; this module is the only write path.
"""

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from usf_audit.models import AuditLog, AuditLogCreate


async def write_audit_log(
    session: AsyncSession,
    payload: AuditLogCreate,
) -> AuditLog:
    """Write an immutable audit log entry."""
    log = AuditLog(**payload.model_dump())
    session.add(log)
    await session.commit()
    await session.refresh(log)
    logger.info(
        "Audit log written",
        extra={
            "id": str(log.id),
            "tenant_id": log.tenant_id,
            "action": log.action,
            "status": log.status,
        },
    )
    return log
