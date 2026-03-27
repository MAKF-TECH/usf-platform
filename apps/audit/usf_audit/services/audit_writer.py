from __future__ import annotations

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession
from usf_audit.models import AuditLog, AuditLogCreate


async def write_audit_log(session: AsyncSession, payload: AuditLogCreate) -> AuditLog:
    """Append-only AuditLog write. No UPDATE/DELETE allowed (enforced by PostgreSQL RLS)."""
    log = AuditLog(**payload.model_dump())
    session.add(log)
    await session.commit()
    await session.refresh(log)
    logger.info("Audit log written", extra={"id": str(log.id), "tenant_id": log.tenant_id, "action": log.action, "status": log.status})
    return log
