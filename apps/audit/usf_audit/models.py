from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlmodel import Column, Field as SField, JSON, SQLModel


class AuditAction(str, Enum):
    QUERY = "query"
    INGEST = "ingest"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    SCHEMA_CHANGE = "schema_change"
    POLICY_CHANGE = "policy_change"


class AuditStatus(str, Enum):
    SUCCESS = "success"
    DENIED = "denied"
    ERROR = "error"


class AuditLog(SQLModel, table=True):
    """Append-only audit log table — writes enforced by PostgreSQL RLS."""
    __tablename__ = "audit_log"

    id: uuid.UUID = SField(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: str = SField(index=True)
    user_id: str | None = SField(default=None, index=True)
    context: str | None = None
    action: AuditAction
    status: AuditStatus
    query_hash: str | None = SField(default=None, index=True)
    resource_iri: str | None = None
    prov_jsonld: dict[str, Any] = SField(default_factory=dict, sa_column=Column(JSON))
    metadata: dict[str, Any] = SField(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = SField(default_factory=datetime.utcnow, index=True)


class AuditLogRead(BaseModel):
    id: uuid.UUID
    tenant_id: str
    user_id: str | None
    context: str | None
    action: AuditAction
    status: AuditStatus
    query_hash: str | None
    resource_iri: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogCreate(BaseModel):
    tenant_id: str
    user_id: str | None = None
    context: str | None = None
    action: AuditAction
    status: AuditStatus
    query_hash: str | None = None
    resource_iri: str | None = None
    prov_jsonld: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExportRequest(BaseModel):
    tenant_id: str
    start: datetime
    end: datetime
    format: str = "jsonld"
