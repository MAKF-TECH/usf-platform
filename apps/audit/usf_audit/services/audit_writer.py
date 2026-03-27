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


async def write_query_audit(
    session: AsyncSession,
    tenant_id: str,
    user_id: str | None,
    context: str | None,
    query_hash: str,
    prov_graph_uri: str,
    metadata: dict | None = None,
) -> AuditLog:
    """
    Append-only audit entry for a semantic query execution.
    Called by usf-api after every query.
    Stores the PROV-O graph URI as resource_iri for regulatory traceability.
    """
    payload = AuditLogCreate(
        tenant_id=tenant_id,
        user_id=user_id,
        context=context,
        action=AuditAction.QUERY,
        status=AuditStatus.SUCCESS,
        query_hash=query_hash,
        resource_iri=prov_graph_uri,
        prov_jsonld={"prov_graph": prov_graph_uri},
        metadata=metadata or {},
    )
    return await write_audit_log(session, payload)
