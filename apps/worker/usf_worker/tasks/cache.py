from __future__ import annotations

"""Cache tasks — warm and invalidate query result caches."""

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

QUERY_SERVICE_URL = "http://usf-query:8000"


@app.task(
    name="usf_worker.tasks.cache.warm_cache",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
)
def warm_cache(self: Task, tenant_id: str, context: str) -> dict:
    """Pre-warm query result cache for a tenant+context."""
    logger.info("warm_cache started", extra={"tenant_id": tenant_id, "context": context})
    try:
        response = httpx.post(
            f"{QUERY_SERVICE_URL}/cache/warm",
            json={"tenant_id": tenant_id, "context": context},
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()
        logger.info("warm_cache complete", extra={"tenant_id": tenant_id, "context": context})
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"warm_cache failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


@app.task(
    name="usf_worker.tasks.cache.invalidate_cache",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    acks_late=True,
)
def invalidate_cache(self: Task, tenant_id: str, metric: str) -> dict:
    """Invalidate cached results for a specific tenant+metric."""
    logger.info("invalidate_cache", extra={"tenant_id": tenant_id, "metric": metric})
    try:
        response = httpx.delete(
            f"{QUERY_SERVICE_URL}/cache",
            params={"tenant_id": tenant_id, "metric": metric},
            timeout=30,
        )
        response.raise_for_status()
        return {"status": "success", "tenant_id": tenant_id, "metric": metric}
    except Exception as exc:
        logger.error(f"invalidate_cache failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
