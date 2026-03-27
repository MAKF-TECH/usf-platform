from __future__ import annotations

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

SDL_URL = "http://usf-sdl:8000"
KG_URL = "http://usf-kg:8000"


@app.task(name="usf_worker.tasks.sdl.recompile_sdl", bind=True, max_retries=3, default_retry_delay=30, acks_late=True)
def recompile_sdl(self: Task, sdl_version_id: str) -> dict:
    logger.info("recompile_sdl", extra={"sdl_version_id": sdl_version_id})
    try:
        r = httpx.post(f"{SDL_URL}/compile", json={"version_id": sdl_version_id}, timeout=120)
        r.raise_for_status()
        return {"status": "success", "sdl_version_id": sdl_version_id, **r.json()}
    except Exception as exc:
        logger.error(f"recompile_sdl failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


@app.task(name="usf_worker.tasks.sdl.validate_all_triples", bind=True, max_retries=2, default_retry_delay=60, acks_late=True)
def validate_all_triples(self: Task, named_graph_uri: str) -> dict:
    logger.info("validate_all_triples", extra={"named_graph": named_graph_uri})
    try:
        r = httpx.post(f"{KG_URL}/shacl/validate", json={"named_graph_uri": named_graph_uri}, timeout=300)
        r.raise_for_status()
        return {"status": "success", **r.json()}
    except Exception as exc:
        logger.error(f"validate_all_triples failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
