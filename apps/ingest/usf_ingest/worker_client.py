from __future__ import annotations

"""Worker client — thin HTTP/Celery dispatch wrapper used by routers.

Avoids importing the full Celery app inside the FastAPI process.
Uses .send_task() with the broker URL from settings (fire-and-forget).
"""

import celery

from usf_ingest.config import get_settings


def _get_celery_app() -> celery.Celery:
    settings = get_settings()
    app = celery.Celery(broker=settings.VALKEY_URL)
    app.conf.task_serializer = "json"
    app.conf.accept_content = ["json"]
    return app


async def dispatch_ingest_job(job_id: str, source_id: str, incremental: bool) -> str:
    app = _get_celery_app()
    result = app.send_task(
        "usf_worker.tasks.ingest.ingest_structured_source",
        kwargs={"job_id": job_id, "source_id": source_id, "incremental": incremental},
        task_id=f"ingest-{job_id}",
    )
    return result.id


async def dispatch_ontorag_pipeline(
    tenant_id: str,
    named_graph_uri: str | None,
    force_reload: bool,
) -> str:
    app = _get_celery_app()
    result = app.send_task(
        "usf_worker.tasks.ontology.sync_ontology_module",
        kwargs={
            "tenant_id": tenant_id,
            "named_graph_uri": named_graph_uri,
            "force_reload": force_reload,
        },
    )
    return result.id
