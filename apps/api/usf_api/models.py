from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Column, Field as SQLField, SQLModel

try:
    from sqlalchemy import JSON as JSONB
except ImportError:
    JSONB = None  # type: ignore


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


# ── SQLModel DB tables ──────────────────────────────────────────────────────

class Tenant(SQLModel, table=True):
    __tablename__ = "tenant"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    name: str
    industry: str
    slug: str = SQLField(unique=True, index=True)
    ontology_module: str
    kg_namespace: str
    plan: str = SQLField(default="trial")
    created_at: datetime = SQLField(default_factory=utcnow)


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = SQLField(foreign_key="tenant.id", index=True)
    email: str = SQLField(unique=True, index=True)
    hashed_password: str
    role: str  # admin | analyst | viewer | auditor
    department: str | None = None
    clearance_level: str = SQLField(default="internal")
    is_active: bool = SQLField(default=True)
    created_at: datetime = SQLField(default_factory=utcnow)


class Session(SQLModel, table=True):
    __tablename__ = "session"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = SQLField(foreign_key="user.id", index=True)
    refresh_token_hash: str = SQLField(index=True)
    expires_at: datetime
    created_at: datetime = SQLField(default_factory=utcnow)
    revoked: bool = SQLField(default=False)


# ── Pydantic request/response models ────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    department: str | None
    tenant_id: uuid.UUID


class QueryRequest(BaseModel):
    question: str | None = None
    sparql: str | None = None
    sql: str | None = None
    metric: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    time_range: dict[str, str] | None = None
    max_results: int = Field(default=100, le=1000)
    mode: str = Field(default="auto", pattern="^(auto|sparql|sql|nl|ograg)$")


class ContextAmbiguousResponse(BaseModel):
    error: str = "context_ambiguous"
    metric: str | None = None
    available_contexts: list[str] = Field(default_factory=list)
    hint: str = "Set X-USF-Context header"


class AuditLog(SQLModel, table=True):
    """Immutable audit trail for all query operations."""
    __tablename__ = "audit_log"

    id: uuid.UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = SQLField(foreign_key="user.id", index=True)
    tenant_id: uuid.UUID = SQLField(foreign_key="tenant.id", index=True)
    query_hash: str = SQLField(index=True)
    context: str | None = None
    metric: str | None = None
    backend: str | None = None
    abac_decision: str = "permit"
    cache_hit: bool = SQLField(default=False)
    execution_ms: float | None = None
    created_at: datetime = SQLField(default_factory=utcnow, index=True)
    error: str | None = None
