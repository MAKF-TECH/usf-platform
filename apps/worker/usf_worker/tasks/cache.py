from __future__ import annotations

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

QUERY_URL = "http://usf-query:8000"


@app.task(name="usf_worker.tasks.cache.warm_cache", bind=True, max_retries=3, default_retry_delay=15, acks_late=True)
def warm_cache(self: Task, tenant_id: str, context: str) -> dict:
    logger.info("warm_cache", extra={"tenant_id": tenant_id, "context": context})
    try:
        r = httpx.post(f"{QUERY_URL}/cache/warm", json={"tenant_id": tenant_id, "context": context}, timeout=120)
        r.raise_for_status()
        return {"status": "success", **r.json()}
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


@app.task(name="usf_worker.tasks.cache.invalidate_cache", bind=True, max_retries=2, default_retry_delay=5, acks_late=True)
def invalidate_cache(self: Task, tenant_id: str, metric: str) -> dict:
    logger.info("invalidate_cache", extra={"tenant_id": tenant_id, "metric": metric})
    try:
        r = httpx.delete(f"{QUERY_URL}/cache", params={"tenant_id": tenant_id, "metric": metric}, timeout=30)
        r.raise_for_status()
        return {"status": "success", "tenant_id": tenant_id, "metric": metric}
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
