from __future__ import annotations
<<<<<<< HEAD

from fastapi import APIRouter, BackgroundTasks
from loguru import logger
from pydantic import BaseModel

=======
from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
from usf_ingest.worker_client import dispatch_ontorag_pipeline

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])

<<<<<<< HEAD

=======
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
class OntoRAGRequest(BaseModel):
    tenant_id: str
    named_graph_uri: str | None = None
    force_reload: bool = False

<<<<<<< HEAD

@router.post("/ontorag", status_code=202)
async def bootstrap_ontorag(payload: OntoRAGRequest) -> dict:
    """Trigger OntoRAG pipeline bootstrap via Celery."""
    task_id = await dispatch_ontorag_pipeline(
        tenant_id=payload.tenant_id,
        named_graph_uri=payload.named_graph_uri,
        force_reload=payload.force_reload,
    )
    logger.info("OntoRAG bootstrap triggered", extra={"tenant_id": payload.tenant_id, "task_id": task_id})
=======
@router.post("/ontorag", status_code=202)
async def bootstrap_ontorag(payload: OntoRAGRequest) -> dict:
    task_id = await dispatch_ontorag_pipeline(payload.tenant_id, payload.named_graph_uri, payload.force_reload)
    logger.info("OntoRAG bootstrap", extra={"tenant_id": payload.tenant_id, "task_id": task_id})
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
    return {"status": "accepted", "task_id": task_id, "tenant_id": payload.tenant_id}
