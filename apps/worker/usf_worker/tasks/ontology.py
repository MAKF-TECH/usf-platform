from __future__ import annotations

"""Ontology tasks — sync ontology modules to the KG."""

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

KG_SERVICE_URL = "http://usf-kg:8000"


@app.task(
    name="usf_worker.tasks.ontology.sync_ontology_module",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def sync_ontology_module(
    self: Task,
    module_id: str | None = None,
    version: str | None = None,
    tenant_id: str | None = None,
    named_graph_uri: str | None = None,
    force_reload: bool = False,
) -> dict:
    """
    Idempotent ontology module sync task.

    Pulls the specified ontology module version from the ontologies package
    and loads it into the USF Knowledge Graph.
    """
    logger.info(
        "sync_ontology_module started",
        extra={"module_id": module_id, "version": version, "force": force_reload},
    )
    try:
        payload: dict = {"force_reload": force_reload}
        if module_id:
            payload["module_id"] = module_id
        if version:
            payload["version"] = version
        if named_graph_uri:
            payload["named_graph_uri"] = named_graph_uri
        if tenant_id:
            payload["tenant_id"] = tenant_id

        response = httpx.post(
            f"{KG_SERVICE_URL}/ontology/sync",
            json=payload,
            timeout=180,
        )
        response.raise_for_status()
        result = response.json()
        logger.info("sync_ontology_module complete", extra=result)
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"sync_ontology_module failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
