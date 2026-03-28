"""USF SQLModel table definitions."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)

class Tenant(SQLModel, table=True):
    __tablename__ = "tenant"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    industry: str
    slug: str = Field(unique=True)
    ontology_module: str
    kg_namespace: str = Field(unique=True)
    plan: str = Field(default="trial")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    email: str = Field(unique=True)
    hashed_password: str
    role: str = Field(default="viewer")
    department: Optional[str] = None
    clearance_level: str = Field(default="internal")
    is_active: bool = Field(default=True)
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="usf.user.id")
    token_hash: str = Field(unique=True)
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)

class DataSource(SQLModel, table=True):
    __tablename__ = "data_source"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    name: str
    type: str
    subtype: str
    connection_config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    schema_snapshot: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    status: str = Field(default="pending")
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

class IngestionJob(SQLModel, table=True):
    __tablename__ = "ingestion_job"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    source_id: uuid.UUID = Field(foreign_key="usf.data_source.id")
    celery_task_id: Optional[str] = None
    status: str = Field(default="pending")
    mode: str = Field(default="full")
    triples_added: int = Field(default=0)
    triples_quarantined: int = Field(default=0)
    documents_processed: int = Field(default=0)
    extraction_model: Optional[str] = None
    ontology_version: Optional[str] = None
    openlineage_run_id: Optional[str] = None
    named_graph_uri: Optional[str] = None
    trace: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None

class SDLVersion(SQLModel, table=True):
    __tablename__ = "sdl_version"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    version: str
    content_yaml: str
    compiled_owl: Optional[str] = None
    compiled_sql: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    compiled_r2rml: Optional[str] = None
    shacl_shapes: Optional[str] = None
    named_graph_uri: Optional[str] = None
    is_active: bool = Field(default=False)
    changelog: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by: Optional[uuid.UUID] = Field(default=None, foreign_key="usf.user.id")
    created_at: datetime = Field(default_factory=_utcnow)

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="usf.user.id")
    action: str
    context: Optional[str] = None
    metric_or_entity: Optional[str] = None
    abac_decision: str = Field(default="permit")
    abac_policy_version: Optional[str] = None
    abac_filter_applied: Optional[str] = None
    query_hash: Optional[str] = None
    query_type: Optional[str] = None
    prov_o_graph_uri: Optional[str] = None
    named_graph_uri: Optional[str] = None
    execution_ms: Optional[int] = None
    row_count: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)

class JobRun(SQLModel, table=True):
    __tablename__ = "job_run"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    celery_task_id: str = Field(unique=True)
    task_name: str
    status: str = Field(default="pending")
    args: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    result: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    error: Optional[str] = None
    retry_count: int = Field(default=0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)

class OntologyModule(SQLModel, table=True):
    __tablename__ = "ontology_module"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    module: str
    version: str
    named_graph_uri: str
    classes_count: int = Field(default=0)
    properties_count: int = Field(default=0)
    shapes_count: int = Field(default=0)
    is_active: bool = Field(default=True)
    loaded_at: datetime = Field(default_factory=_utcnow)

class ContextDef(SQLModel, table=True):
    __tablename__ = "context_definition"
    __table_args__ = {"schema": "usf"}
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    sdl_version_id: Optional[uuid.UUID] = Field(default=None, foreign_key="usf.sdl_version.id")
    name: str
    description: str
    named_graph_uri: str
    parent_context: Optional[str] = None
    version: int = Field(default=1)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
