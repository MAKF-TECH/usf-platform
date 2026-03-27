from __future__ import annotations

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

KG_URL = "http://usf-kg:8000"


@app.task(name="usf_worker.tasks.ontology.sync_ontology_module", bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def sync_ontology_module(
    self: Task,
    module_id: str | None = None,
    version: str | None = None,
    tenant_id: str | None = None,
    named_graph_uri: str | None = None,
    force_reload: bool = False,
) -> dict:
    """Idempotent ontology module sync."""
    logger.info("sync_ontology_module", extra={"module_id": module_id, "version": version, "force": force_reload})
    try:
        payload = {"force_reload": force_reload}
        for k, v in [("module_id", module_id), ("version", version), ("named_graph_uri", named_graph_uri), ("tenant_id", tenant_id)]:
            if v is not None:
                payload[k] = v
        r = httpx.post(f"{KG_URL}/ontology/sync", json=payload, timeout=180)
        r.raise_for_status()
        return {"status": "success", **r.json()}
    except Exception as exc:
        logger.error(f"sync_ontology_module failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
