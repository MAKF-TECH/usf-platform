from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from usf_ingest.db import get_session
from usf_ingest.models import DataSource, IngestionJob, JobCreate, JobRead
from usf_ingest.worker_client import dispatch_ingest_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def trigger_job(
    payload: JobCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JobRead:
    # Verify source exists
    source = await session.get(DataSource, payload.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.is_active:
        raise HTTPException(status_code=400, detail="Source is inactive")

    job = IngestionJob(
        source_id=payload.source_id,
        tenant_id=payload.tenant_id,
        incremental=payload.incremental,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Dispatch Celery task
    task_id = await dispatch_ingest_job(
        job_id=str(job.id),
        source_id=str(job.source_id),
        incremental=job.incremental,
    )
    job.celery_task_id = task_id
    session.add(job)
    await session.commit()

    logger.info("Dispatched ingest job", extra={"job_id": str(job.id), "task_id": task_id})
    return JobRead.model_validate(job)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JobRead:
    job = await session.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job)


@router.get("/{job_id}/trace")
async def get_job_trace(
    job_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Return OpenLineage run facet stored on the job."""
    job = await session.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": str(job.id),
        "celery_task_id": job.celery_task_id,
        "run_facet": job.run_facet,
    }
