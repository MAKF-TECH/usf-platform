from __future__ import annotations
import celery
from usf_ingest.config import get_settings

def _app() -> celery.Celery:
    return celery.Celery(broker=get_settings().VALKEY_URL, task_serializer="json")

async def dispatch_ingest_job(job_id: str, source_id: str, incremental: bool) -> str:
    r = _app().send_task(
        "usf_worker.tasks.ingest.ingest_structured_source",
        kwargs={"job_id": job_id, "source_id": source_id, "incremental": incremental},
        task_id=f"ingest-{job_id}",
    )
    return r.id

async def dispatch_ontorag_pipeline(tenant_id: str, named_graph_uri, force_reload: bool) -> str:
    r = _app().send_task(
        "usf_worker.tasks.ontology.sync_ontology_module",
        kwargs={"tenant_id": tenant_id, "named_graph_uri": named_graph_uri, "force_reload": force_reload},
    )
    return r.id
