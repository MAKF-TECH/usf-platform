"""USF SQLModel table definitions.

These models are the single source of truth for:
  - PostgreSQL table structure (via Alembic + SQLAlchemy)
  - API request/response serialization (via Pydantic v2)

Usage:
  from usf_core.db_models import Tenant, User, AuditLog, ...

All IDs are UUID v4. All timestamps are timezone-aware UTC.
JSON columns use SQLAlchemy's postgresql.JSONB dialect type for PostgreSQL.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _uuid4() -> uuid.UUID:
    return uuid.uuid4()


# ─────────────────────────────────────────────────────────────────────────────
# Tenant
# ─────────────────────────────────────────────────────────────────────────────

class Tenant(SQLModel, table=True):
    __tablename__ = "tenant"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(
        default_factory=_uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    name: str
    industry: str  # banking | healthcare | energy | ...
    slug: str = Field(unique=True)
    ontology_module: str  # fibo | fhir | iec-cim | ...
    kg_namespace: str = Field(unique=True)  # usf://{slug}/
    plan: str = Field(default="trial")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(
        default_factory=_uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
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


# ─────────────────────────────────────────────────────────────────────────────
# RefreshToken
# ─────────────────────────────────────────────────────────────────────────────

class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_token"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(default_factory=_uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="usf.user.id")
    token_hash: str = Field(unique=True)
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# DataSource
# ─────────────────────────────────────────────────────────────────────────────

class DataSource(SQLModel, table=True):
    __tablename__ = "data_source"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(default_factory=_uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    name: str
    type: str  # warehouse | file | api | stream
    subtype: str  # snowflake | postgres | pdf | fhir | ...
    connection_config: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    schema_snapshot: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    status: str = Field(default="pending")
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# IngestionJob
# ─────────────────────────────────────────────────────────────────────────────

class IngestionJob(SQLModel, table=True):
    __tablename__ = "ingestion_job"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(default_factory=_uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    source_id: uuid.UUID = Field(foreign_key="usf.data_source.id")
    celery_task_id: Optional[str] = None
    status: str = Field(default="pending")  # pending|running|complete|failed|cancelled
    mode: str = Field(default="full")  # full | incremental
    triples_added: int = Field(default=0)
    triples_quarantined: int = Field(default=0)
    documents_processed: int = Field(default=0)
    extraction_model: Optional[str] = None
    ontology_version: Optional[str] = None
    openlineage_run_id: Optional[str] = None
    named_graph_uri: Optional[str] = None
    trace: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=_utcnow)
    completed_at: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# SDLVersion
# ─────────────────────────────────────────────────────────────────────────────

class SDLVersion(SQLModel, table=True):
    __tablename__ = "sdl_version"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(default_factory=_uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    version: str  # e.g. v1, v2, v3
    content_yaml: str
    compiled_owl: Optional[str] = None  # Turtle serialization
    compiled_sql: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    compiled_r2rml: Optional[str] = None
    shacl_shapes: Optional[str] = None
    named_graph_uri: Optional[str] = None
    is_active: bool = Field(default=False)
    changelog: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by: Optional[uuid.UUID] = Field(default=None, foreign_key="usf.user.id")
    created_at: datetime = Field(default_factory=_utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# AuditLog
# ─────────────────────────────────────────────────────────────────────────────

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(default_factory=_uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="usf.user.id")
    action: str  # query | ingest | sdl_publish | login | ...
    context: Optional[str] = None
    metric_or_entity: Optional[str] = None
    abac_decision: str = Field(default="permit")  # permit | permit_with_filter | deny
    abac_policy_version: Optional[str] = None
    abac_filter_applied: Optional[str] = None
    query_hash: Optional[str] = None
    query_type: Optional[str] = None
    prov_o_graph_uri: Optional[str] = None
    named_graph_uri: Optional[str] = None
    execution_ms: Optional[int] = None
    row_count: Optional[int] = None
    ip_address: Optional[str] = None  # Stored as text; DB uses INET type
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# JobRun (Celery task tracking)
# ─────────────────────────────────────────────────────────────────────────────

class JobRun(SQLModel, table=True):
    __tablename__ = "job_run"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(default_factory=_uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    celery_task_id: str = Field(unique=True)
    task_name: str
    status: str = Field(default="pending")  # pending|running|success|failure|retry|revoked
    args: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    result: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    error: Optional[str] = None
    retry_count: int = Field(default=0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# OntologyModule
# ─────────────────────────────────────────────────────────────────────────────

class OntologyModule(SQLModel, table=True):
    __tablename__ = "ontology_module"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(default_factory=_uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    module: str  # fibo | fhir | iec-cim | ...
    version: str  # 2024-Q4
    named_graph_uri: str
    classes_count: int = Field(default=0)
    properties_count: int = Field(default=0)
    shapes_count: int = Field(default=0)
    is_active: bool = Field(default=True)
    loaded_at: datetime = Field(default_factory=_utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# ContextDef
# ─────────────────────────────────────────────────────────────────────────────

class ContextDef(SQLModel, table=True):
    """Persisted semantic context (mirrors SDL context block)."""
    __tablename__ = "context_definition"
    __table_args__ = {"schema": "usf"}

    id: uuid.UUID = Field(default_factory=_uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="usf.tenant.id")
    sdl_version_id: Optional[uuid.UUID] = Field(default=None, foreign_key="usf.sdl_version.id")
    name: str
    description: str
    named_graph_uri: str
    parent_context: Optional[str] = None
    version: int = Field(default=1)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
