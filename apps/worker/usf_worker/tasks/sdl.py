from __future__ import annotations

"""SDL tasks — recompile and validate SDL/triples."""

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

SDL_SERVICE_URL = "http://usf-sdl:8000"
KG_SERVICE_URL = "http://usf-kg:8000"


@app.task(
    name="usf_worker.tasks.sdl.recompile_sdl",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def recompile_sdl(self: Task, sdl_version_id: str) -> dict:
    """Idempotent SDL recompilation task."""
    logger.info("recompile_sdl started", extra={"sdl_version_id": sdl_version_id})
    try:
        response = httpx.post(
            f"{SDL_SERVICE_URL}/compile",
            json={"version_id": sdl_version_id},
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()
        logger.info("recompile_sdl complete", extra={"result": result})
        return {"status": "success", "sdl_version_id": sdl_version_id, **result}
    except Exception as exc:
        logger.error(f"recompile_sdl failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


@app.task(
    name="usf_worker.tasks.sdl.validate_all_triples",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def validate_all_triples(self: Task, named_graph_uri: str) -> dict:
    """Run SHACL validation over all triples in a named graph."""
    logger.info("validate_all_triples started", extra={"named_graph": named_graph_uri})
    try:
        response = httpx.post(
            f"{KG_SERVICE_URL}/shacl/validate",
            json={"named_graph_uri": named_graph_uri},
            timeout=300,
        )
        response.raise_for_status()
        result = response.json()
        violations = result.get("violations", 0)
        logger.info(
            "validate_all_triples complete",
            extra={"named_graph": named_graph_uri, "violations": violations},
        )
        return {"status": "success", "violations": violations, **result}
    except Exception as exc:
        logger.error(f"validate_all_triples failed: {exc}")
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
