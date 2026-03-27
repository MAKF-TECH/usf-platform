from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class ErrorDetail(BaseModel):
    code: str
    message: str
    hint: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProvenanceBlock(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    executed_at: datetime = Field(default_factory=utcnow)
    context: str | None = None
    query_hash: str | None = None
    abac_decision: str | None = None
    prov_o: dict[str, Any] = Field(default_factory=dict)


class ResponseMeta(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=utcnow)
    version: str = "1.0"
    service: str = "usf"


class ResponseEnvelope(BaseModel, Generic[T]):
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    data: T | None = None
    schema_ref: str | None = None
    provenance: ProvenanceBlock | None = None
    error: ErrorDetail | None = None
