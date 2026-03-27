from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from usf_ingest.db import get_session
from usf_ingest.models import DataSource, DataSourceCreate, DataSourceRead

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=DataSourceRead, status_code=status.HTTP_201_CREATED)
async def register_source(
    payload: DataSourceCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DataSourceRead:
    source = DataSource(**payload.model_dump())
    session.add(source)
    await session.commit()
    await session.refresh(source)
    logger.info("Registered data source", extra={"source_id": str(source.id), "type": source.source_type})
    return DataSourceRead.model_validate(source)


@router.get("", response_model=list[DataSourceRead])
async def list_sources(
    session: Annotated[AsyncSession, Depends(get_session)],
    tenant_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[DataSourceRead]:
    stmt = select(DataSource).where(DataSource.is_active == True)
    if tenant_id:
        stmt = stmt.where(DataSource.tenant_id == tenant_id)
    stmt = stmt.offset(offset).limit(limit)
    result = await session.exec(stmt)
    return [DataSourceRead.model_validate(s) for s in result.all()]


@router.get("/{source_id}", response_model=DataSourceRead)
async def get_source(
    source_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DataSourceRead:
    source = await session.get(DataSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return DataSourceRead.model_validate(source)
