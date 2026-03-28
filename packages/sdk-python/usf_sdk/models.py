"""USF SDK — Pydantic response models."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None


# ── Metrics ───────────────────────────────────────────────────────────────────

class MetricSummary(BaseModel):
    name: str
    description: str
    ontology_class: str
    type: str
    contexts: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    time_grains: list[str] = Field(default_factory=list)


class MetricExplanation(BaseModel):
    name: str
    description: str
    ontology_class: str
    type: str
    compiled_sql: str | None = None
    compiled_sparql: str | None = None
    source_tables: list[str] = Field(default_factory=list)
    sdl_version: str | None = None
    lineage: dict[str, Any] = Field(default_factory=dict)


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryMeta(BaseModel):
    request_id: str | None = None
    tenant_id: str | None = None
    context: str | None = None
    named_graph: str | None = None
    query_hash: str | None = None
    prov_o_uri: str | None = None
    cached: bool = False
    execution_ms: int | None = None


class QueryResult(BaseModel):
    columns: list[str] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    meta: QueryMeta = Field(default_factory=QueryMeta)

    @property
    def provenance(self) -> dict[str, Any]:
        """Convenience access to PROV-O provenance block."""
        return {
            "prov:wasGeneratedBy": {
                "usf:contextApplied": self.meta.context,
                "usf:namedGraph": self.meta.named_graph,
                "usf:queryHash": self.meta.query_hash,
                "usf:provOUri": self.meta.prov_o_uri,
            }
        }


# ── Knowledge Graph ───────────────────────────────────────────────────────────

class KgNode(BaseModel):
    iri: str
    label: str
    ontology_class: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    prov_o: dict[str, Any] = Field(default_factory=dict)


class EntityResult(BaseModel):
    iri: str
    label: str
    ontology_class: str | None = None
    score: float | None = None


class EntityDetail(BaseModel):
    iri: str
    label: str
    ontology_class: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    neighbors: list[dict[str, Any]] = Field(default_factory=list)
    prov_o: dict[str, Any] = Field(default_factory=dict)


# ── Context ───────────────────────────────────────────────────────────────────

class ContextInfo(BaseModel):
    name: str
    description: str | None = None
    named_graph_uri: str | None = None
    metric_count: int = 0
