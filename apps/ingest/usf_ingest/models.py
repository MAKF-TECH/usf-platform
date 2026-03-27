from __future__ import annotations
<<<<<<< HEAD

=======
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
import uuid
from datetime import datetime
from enum import Enum
from typing import Any
<<<<<<< HEAD

from pydantic import BaseModel, Field
from sqlmodel import Column, Field as SField, JSON, SQLModel


class SourceType(str, Enum):
    CSV = "csv"
    PARQUET = "parquet"
    POSTGRES = "postgres"
    REST_API = "rest_api"
    FHIR = "fhir"
    CIM = "cim"
    JSONLD = "jsonld"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class DataSource(SQLModel, table=True):
    __tablename__ = "data_sources"

=======
from pydantic import BaseModel, Field
from sqlmodel import Column, Field as SField, JSON, SQLModel

class SourceType(str, Enum):
    CSV = "csv"; PARQUET = "parquet"; POSTGRES = "postgres"
    REST_API = "rest_api"; FHIR = "fhir"; CIM = "cim"; JSONLD = "jsonld"

class JobStatus(str, Enum):
    PENDING = "pending"; RUNNING = "running"; SUCCESS = "success"
    FAILED = "failed"; RETRYING = "retrying"

class DataSource(SQLModel, table=True):
    __tablename__ = "data_sources"
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
    id: uuid.UUID = SField(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: str = SField(index=True)
    name: str
    source_type: SourceType
    connection_config: dict[str, Any] = SField(default_factory=dict, sa_column=Column(JSON))
    metadata: dict[str, Any] = SField(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = SField(default_factory=datetime.utcnow)
    updated_at: datetime = SField(default_factory=datetime.utcnow)
    is_active: bool = True

<<<<<<< HEAD

class IngestionJob(SQLModel, table=True):
    __tablename__ = "ingestion_jobs"

=======
class IngestionJob(SQLModel, table=True):
    __tablename__ = "ingestion_jobs"
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
    id: uuid.UUID = SField(default_factory=uuid.uuid4, primary_key=True)
    source_id: uuid.UUID = SField(foreign_key="data_sources.id", index=True)
    tenant_id: str = SField(index=True)
    status: JobStatus = JobStatus.PENDING
    celery_task_id: str | None = None
    incremental: bool = True
    records_processed: int = 0
    triples_added: int = 0
    triples_quarantined: int = 0
    shacl_violations: int = 0
    error_message: str | None = None
    run_facet: dict[str, Any] = SField(default_factory=dict, sa_column=Column(JSON))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = SField(default_factory=datetime.utcnow)

<<<<<<< HEAD

class DataSourceCreate(BaseModel):
    tenant_id: str
    name: str
    source_type: SourceType
    connection_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataSourceRead(BaseModel):
    id: uuid.UUID
    tenant_id: str
    name: str
    source_type: SourceType
    connection_config: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class JobCreate(BaseModel):
    source_id: uuid.UUID
    tenant_id: str
    incremental: bool = True


class JobRead(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    tenant_id: str
    status: JobStatus
    celery_task_id: str | None
    incremental: bool
    records_processed: int
    triples_added: int
    triples_quarantined: int
    shacl_violations: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

=======
class DataSourceCreate(BaseModel):
    tenant_id: str; name: str; source_type: SourceType
    connection_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

class DataSourceRead(BaseModel):
    id: uuid.UUID; tenant_id: str; name: str; source_type: SourceType
    connection_config: dict[str, Any]; metadata: dict[str, Any]
    created_at: datetime; is_active: bool
    model_config = {"from_attributes": True}

class JobCreate(BaseModel):
    source_id: uuid.UUID; tenant_id: str; incremental: bool = True

class JobRead(BaseModel):
    id: uuid.UUID; source_id: uuid.UUID; tenant_id: str; status: JobStatus
    celery_task_id: str | None; incremental: bool; records_processed: int
    triples_added: int; triples_quarantined: int; shacl_violations: int
    error_message: str | None; started_at: datetime | None
    finished_at: datetime | None; created_at: datetime
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
    model_config = {"from_attributes": True}
