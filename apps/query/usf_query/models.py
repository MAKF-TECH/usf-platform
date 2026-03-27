from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    SQL = "sql"
    SPARQL = "sparql"
    NL = "nl"
    OGRAG = "ograg"


class QueryBackend(str, Enum):
    QLEVER = "qlever"
    ARCADEDB = "arcadedb"
    WREN = "wren"
    ONTOP = "ontop"
    HYBRID = "hybrid"


class SemanticQuery(BaseModel):
    query: str
    query_type: QueryType
    context: str | None = None
    tenant_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    total_rows: int = 0
    backend_used: QueryBackend | None = None
    execution_time_ms: float | None = None
    query_hash: str | None = None
    sparql_generated: str | None = None
    sql_generated: str | None = None


class NLQueryRequest(BaseModel):
    question: str
    context: str | None = None
    tenant_id: str | None = None
    ontology_context: str | None = None
    max_results: int = Field(default=100, le=1000)


class OGRagRequest(BaseModel):
    question: str
    context: str | None = None
    tenant_id: str | None = None
    k: int = Field(default=5, ge=1, le=20)
    max_depth: int = Field(default=2, ge=1, le=4)


class CompileRequest(BaseModel):
    metric_name: str
    context: str
    tenant_id: str | None = None
    dialect: str = Field(default="postgres", pattern="^(postgres|snowflake|bigquery)$")


class CompiledQuery(BaseModel):
    metric_name: str
    context: str
    sql: str
    sparql: str
    dialect: str
    ontology_class: str | None = None


class MetricDefinition(BaseModel):
    name: str
    description: str | None = None
    ontology_class: str | None = None
    contexts: list[str] = Field(default_factory=list)
    sql_template: str | None = None
    sparql_template: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    lineage: dict[str, Any] = Field(default_factory=dict)


class Hyperedge(BaseModel):
    """A cluster of related RDF triples grounded by an ontology class."""

    id: str
    ontology_class: str
    triples: list[tuple[str, str, str]] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    source_graph: str | None = None
