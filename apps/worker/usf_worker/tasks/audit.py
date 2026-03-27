from __future__ import annotations

"""Audit tasks — export audit logs for a period."""

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

AUDIT_SERVICE_URL = "http://usf-audit:8000"


@app.task(
    name="usf_worker.tasks.audit.export_audit_period",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def export_audit_period(
    self: Task,
    tenant_id: str,
    start: str,   # ISO 8601
    end: str,     # ISO 8601
    format: str = "jsonld",  # "jsonld" | "turtle"
) -> dict:
    """Export audit logs + PROV-O traces for a tenant over a time period."""
    logger.info(
        "export_audit_period started",
        extra={"tenant_id": tenant_id, "start": start, "end": end, "format": format},
    )
    try:
        response = httpx.post(
            f"{AUDIT_SERVICE_URL}/export",
            json={"tenant_id": tenant_id, "start": start, "end": end, "format": format},
            timeout=300,
        )
        response.raise_for_status()
        result = response.json()
        logger.info("export_audit_period complete", extra={"tenant_id": tenant_id})
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"export_audit_period failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
