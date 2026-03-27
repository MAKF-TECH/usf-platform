"""Pydantic request/response models for usf-kg endpoints."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ── Triples ──────────────────────────────────────────────────────────────────

class TripleIn(BaseModel):
    subject: str
    predicate: str
    object: str


class BulkInsertRequest(BaseModel):
    graph_uri: str = Field(..., description="Named graph URI to insert triples into")
    triples: list[TripleIn] = Field(..., min_length=1)


class BulkInsertResponse(BaseModel):
    graph_uri: str
    inserted: int
    message: str = "ok"


# ── Graphs ────────────────────────────────────────────────────────────────────

class GraphSummary(BaseModel):
    uri: str
    triple_count: int | None = None


class GraphListResponse(BaseModel):
    graphs: list[GraphSummary]
    total: int


# ── Entities ──────────────────────────────────────────────────────────────────

class EntityProperty(BaseModel):
    predicate: str
    value: str
    datatype: str | None = None
    source_graph: str | None = None


class EntityDetail(BaseModel):
    iri: str
    types: list[str]
    properties: list[EntityProperty]
    prov_graph: str | None = None


class EntityResolveRequest(BaseModel):
    candidate_iris: list[str] = Field(..., min_length=2)
    strategy: str = Field(default="levenshtein", description="Resolution strategy: levenshtein | owl_sameAs")


class EntityResolveResponse(BaseModel):
    canonical_iri: str
    merged_iris: list[str]
    confidence: float


# ── Validation ────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    graph_uri: str
    shapes_graph_uri: str | None = None
    shapes_turtle: str | None = None


class ViolationOut(BaseModel):
    focus_node: str
    result_path: str | None
    value: str | None
    source_shape: str | None
    message: str
    severity: str


class ValidateResponse(BaseModel):
    conforms: bool
    violations: list[ViolationOut]
    quarantined_graph: str | None = None


# ── Ontology ──────────────────────────────────────────────────────────────────

class OntologyLoadRequest(BaseModel):
    turtle_content: str | None = None
    turtle_url: str | None = None
    named_graph: str = Field(..., description="Target named graph URI")
    resolve_imports: bool = False


class OntologyLoadResponse(BaseModel):
    named_graph: str
    triples_loaded: int
    message: str = "ok"


# ── Provenance ────────────────────────────────────────────────────────────────

class ProvenanceResponse(BaseModel):
    entity_iri: str
    prov_o: dict[str, Any]
