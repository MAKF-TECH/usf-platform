from __future__ import annotations

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

AUDIT_URL = "http://usf-audit:8000"


@app.task(name="usf_worker.tasks.audit.export_audit_period", bind=True, max_retries=2, default_retry_delay=30, acks_late=True)
def export_audit_period(self: Task, tenant_id: str, start: str, end: str, format: str = "jsonld") -> dict:
    """Export audit logs + PROV-O traces for a tenant/period."""
    logger.info("export_audit_period", extra={"tenant_id": tenant_id, "start": start, "end": end})
    try:
        r = httpx.post(f"{AUDIT_URL}/export", json={"tenant_id": tenant_id, "start": start, "end": end, "format": format}, timeout=300)
        r.raise_for_status()
        return {"status": "success", **r.json()}
    except Exception as exc:
        logger.error(f"export_audit_period failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
