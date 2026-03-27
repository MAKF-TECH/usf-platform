"""
USF SDL Pydantic v2 Models.

All SDL constructs are modelled here. These models are the canonical
source of truth for SDL YAML schema validation.

Design decisions:
- Use Pydantic v2 model_validator for cross-field validation
- All string IDs use pattern validators (no magic strings)
- Optional fields default to None / [] to keep YAML minimal
- No circular references — Entity references other entities by name (string)
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, Field, model_validator, field_validator


# ─────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
PASCAL_CASE_PATTERN = re.compile(r"^[A-Z][a-zA-Z0-9]{0,63}$")
CURIE_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*:[A-Za-z][A-Za-z0-9_-]*$")
SDL_VERSION_PATTERN = re.compile(r"^v\d+$")

VALID_XSD_TYPES = frozenset(
    ["string", "integer", "decimal", "date", "datetime", "boolean", "anyURI", "float"]
)
VALID_AGGREGATION_TYPES = frozenset(
    ["sum", "count", "avg", "min", "max", "count_distinct", "custom"]
)
VALID_TIME_GRAINS = frozenset(["day", "week", "month", "quarter", "year"])
VALID_CLEARANCE_LEVELS = frozenset(
    ["public", "internal", "confidential", "restricted", "top_secret"]
)
VALID_ONTOLOGY_MODULES = frozenset(
    ["fibo", "fhir", "iec-cim", "rami40", "obo", "dcat", "gs1", "sid"]
)


# ─────────────────────────────────────────────────────────────────
# Sub-models
# ─────────────────────────────────────────────────────────────────


class ContextPropertyOverride(BaseModel):
    """Per-context override for a single property."""

    sql_column: str | None = None
    description: str | None = None


class PropertyDefinition(BaseModel):
    """A single property mapping: ontology predicate ↔ SQL column."""

    name: str = Field(..., description="Snake_case property name, unique within entity")
    ontology_property: str = Field(..., description="CURIE: prefix:LocalName")
    sql_column: str | None = Field(
        default=None,
        description="Default SQL column. Optional if all contexts define it.",
    )
    type: str | None = Field(default=None, description="XSD type hint")
    nullable: bool = Field(default=True)
    description: str | None = None
    allowed_values: list[str] = Field(
        default_factory=list,
        description="OWL oneOf / SHACL sh:in restriction",
    )
    contexts: dict[str, ContextPropertyOverride] = Field(
        default_factory=dict,
        description="Per-context sql_column overrides",
    )
    references: "EntityReference | None" = None

    @field_validator("name")
    @classmethod
    def name_snake_case(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]{0,63}$", v):
            raise ValueError(f"Property name must be snake_case: {v!r}")
        return v

    @field_validator("ontology_property")
    @classmethod
    def ontology_property_curie(cls, v: str) -> str:
        if not CURIE_PATTERN.match(v):
            raise ValueError(f"ontology_property must be a CURIE (prefix:LocalName): {v!r}")
        return v

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_XSD_TYPES:
            raise ValueError(f"type must be one of {sorted(VALID_XSD_TYPES)}, got: {v!r}")
        return v

    @model_validator(mode="after")
    def sql_column_or_contexts(self) -> "PropertyDefinition":
        """sql_column is required unless every context provides one."""
        if self.sql_column is None and not self.contexts:
            raise ValueError(
                f"Property '{self.name}': either sql_column or at least one context "
                "with sql_column must be defined"
            )
        return self


class EntityReference(BaseModel):
    """Foreign key reference to another SDL entity."""

    entity: str = Field(..., description="Target entity name (PascalCase)")
    property: str = Field(..., description="Target entity property name")


class ContextEntityOverride(BaseModel):
    """Per-context override at the entity level."""

    description: str | None = None
    sql_table: str | None = None


class DimensionDefinition(BaseModel):
    """A metric dimension: groups query results."""

    name: str = Field(..., description="Snake_case dimension name")
    entity: str = Field(..., description="SDL entity name that provides this dimension")
    property: str = Field(..., description="SDL property name within the entity")
    ontology_property: str = Field(..., description="CURIE for the OWL object/data property")
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_snake_case(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]{0,63}$", v):
            raise ValueError(f"Dimension name must be snake_case: {v!r}")
        return v

    @field_validator("ontology_property")
    @classmethod
    def ontology_property_curie(cls, v: str) -> str:
        if not CURIE_PATTERN.match(v):
            raise ValueError(f"ontology_property must be a CURIE: {v!r}")
        return v


class ContextMetricOverride(BaseModel):
    """Per-context override for a metric."""

    description: str | None = None
    filter: str | None = Field(default=None, description="SQL WHERE clause (no WHERE keyword)")
    additional_dimensions: list[str] = Field(default_factory=list)


class InlineAccessPolicy(BaseModel):
    """Inline access policy (alternative to referencing a named policy)."""

    read: list[str] = Field(
        default_factory=list,
        description="Role CURIEs: role:slug",
    )
    write: list[str] = Field(default_factory=list)
    pii: bool = False
    clearance: str = "internal"

    @field_validator("clearance")
    @classmethod
    def clearance_valid(cls, v: str) -> str:
        if v not in VALID_CLEARANCE_LEVELS:
            raise ValueError(f"clearance must be one of {sorted(VALID_CLEARANCE_LEVELS)}, got: {v!r}")
        return v

    @field_validator("read", "write", mode="before")
    @classmethod
    def roles_format(cls, v: list[str]) -> list[str]:
        for role in v:
            if not re.match(r"^role:[a-z][a-z0-9_-]{0,63}$", role):
                raise ValueError(f"Role must match 'role:slug' pattern, got: {role!r}")
        return v


class MetricExample(BaseModel):
    """Example invocation for MCP tool documentation."""

    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────
# Top-level SDL constructs
# ─────────────────────────────────────────────────────────────────


class ContextDefinition(BaseModel):
    """A named business context (e.g., 'finance', 'risk', 'ops')."""

    name: str = Field(..., description="Unique slug identifier")
    description: str = Field(..., description="Human description (shown in UI and MCP)")
    named_graph_uri: str | None = Field(
        default=None,
        description="Computed by the compiler. Do not set manually.",
    )
    parent_context: str | None = Field(
        default=None,
        description="Parent context name. Inherits metrics if set.",
    )
    ontology_scope: list[str] = Field(
        default_factory=list,
        description="OWL class CURIEs visible in this context. Empty = all classes.",
    )

    @field_validator("name")
    @classmethod
    def name_slug(cls, v: str) -> str:
        if not SLUG_PATTERN.match(v):
            raise ValueError(f"Context name must match ^[a-z][a-z0-9_-]{{0,63}}$: {v!r}")
        return v


class EntityDefinition(BaseModel):
    """An SDL entity: maps an ontology class to SQL table(s)."""

    name: str = Field(..., description="PascalCase entity name, unique in SDL")
    ontology_class: str = Field(..., description="CURIE: the OWL class this entity represents")
    description: str = Field(..., description="Human description")
    sql_table: str | None = Field(
        default=None,
        description="Default SQL table. Required unless all contexts define sql_table.",
    )
    sql_schema: str = Field(default="public", description="PostgreSQL schema name")
    contexts: dict[str, ContextEntityOverride] = Field(
        default_factory=dict,
        description="Per-context overrides (description, sql_table)",
    )
    properties: list[PropertyDefinition] = Field(
        ...,
        description="At least one property required",
        min_length=1,
    )
    access_policy: str | InlineAccessPolicy | None = Field(
        default=None,
        description="Named access_policy reference OR inline policy definition",
    )

    @field_validator("name")
    @classmethod
    def name_pascal_case(cls, v: str) -> str:
        if not PASCAL_CASE_PATTERN.match(v):
            raise ValueError(f"Entity name must be PascalCase: {v!r}")
        return v

    @field_validator("ontology_class")
    @classmethod
    def ontology_class_curie(cls, v: str) -> str:
        if not CURIE_PATTERN.match(v):
            raise ValueError(f"ontology_class must be a CURIE: {v!r}")
        return v

    @model_validator(mode="after")
    def property_names_unique(self) -> "EntityDefinition":
        names = [p.name for p in self.properties]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate property names in entity '{self.name}': {duplicates}")
        return self


class MetricDefinition(BaseModel):
    """An SDL metric: a business measure with aggregation logic."""

    name: str = Field(..., description="Snake_case metric name, unique across tenant")
    ontology_class: str = Field(..., description="CURIE: ontology class this metric is an instance of")
    description: str = Field(..., description="Human description")
    type: str = Field(..., description="Aggregation type")
    measure: str = Field(..., description="Column name or expression for the measured quantity")
    measure_entity: str = Field(..., description="SDL entity containing the measure column")
    measure_sql: str | None = Field(
        default=None,
        description="Override compiled SQL expression. Overrides type + measure.",
    )
    dimensions: list[DimensionDefinition] = Field(
        ...,
        description="Grouping dimensions. At least one required.",
        min_length=1,
    )
    contexts: dict[str, ContextMetricOverride] = Field(
        default_factory=dict,
        description="Per-context filter and description overrides",
    )
    default_filter: str | None = Field(
        default=None,
        description="SQL WHERE clause applied before context filter (no WHERE keyword)",
    )
    time_grains: list[str] = Field(default_factory=list)
    time_column: str | None = None
    time_entity: str | None = None
    access_policy: str | InlineAccessPolicy | None = None
    examples: list[MetricExample] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_snake_case(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]{0,79}$", v):
            raise ValueError(f"Metric name must be snake_case: {v!r}")
        return v

    @field_validator("ontology_class")
    @classmethod
    def ontology_class_curie(cls, v: str) -> str:
        if not CURIE_PATTERN.match(v):
            raise ValueError(f"ontology_class must be a CURIE: {v!r}")
        return v

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        if v not in VALID_AGGREGATION_TYPES:
            raise ValueError(f"type must be one of {sorted(VALID_AGGREGATION_TYPES)}, got: {v!r}")
        return v

    @field_validator("time_grains")
    @classmethod
    def time_grains_valid(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_TIME_GRAINS
        if invalid:
            raise ValueError(f"Invalid time_grains: {invalid}. Valid: {sorted(VALID_TIME_GRAINS)}")
        return v

    @model_validator(mode="after")
    def time_grain_requires_column(self) -> "MetricDefinition":
        if self.time_grains and not self.time_column:
            raise ValueError(
                f"Metric '{self.name}': time_column is required when time_grains is non-empty"
            )
        if self.time_grains and not self.time_entity:
            raise ValueError(
                f"Metric '{self.name}': time_entity is required when time_grains is non-empty"
            )
        return self

    @model_validator(mode="after")
    def dimension_names_unique(self) -> "MetricDefinition":
        names = [d.name for d in self.dimensions]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate dimension names in metric '{self.name}'")
        return self


class AccessPolicyDefinition(BaseModel):
    """A named, reusable access policy."""

    name: str = Field(..., description="Unique slug")
    description: str = Field(..., description="Human description")
    read: list[str] = Field(..., description="Role CURIEs with read access", min_length=1)
    write: list[str] = Field(default_factory=list)
    pii: bool = Field(..., description="If true, PII masking rules apply")
    clearance: str = Field(..., description="Data clearance level")
    row_filter: dict[str, str] = Field(
        default_factory=dict,
        description="Per-role SQL WHERE filter injected at query time",
    )

    @field_validator("name")
    @classmethod
    def name_slug(cls, v: str) -> str:
        if not SLUG_PATTERN.match(v):
            raise ValueError(f"Access policy name must be a slug: {v!r}")
        return v

    @field_validator("clearance")
    @classmethod
    def clearance_valid(cls, v: str) -> str:
        if v not in VALID_CLEARANCE_LEVELS:
            raise ValueError(f"clearance must be one of {sorted(VALID_CLEARANCE_LEVELS)}, got: {v!r}")
        return v

    @field_validator("read", "write", mode="before")
    @classmethod
    def roles_format(cls, v: list[str]) -> list[str]:
        for role in v:
            if not re.match(r"^role:[a-z][a-z0-9_-]{0,63}$", role):
                raise ValueError(f"Role must match 'role:slug' pattern, got: {role!r}")
        return v


# ─────────────────────────────────────────────────────────────────
# Root Document
# ─────────────────────────────────────────────────────────────────


class SDLDocument(BaseModel):
    """
    The root SDL document.
    Parsed from YAML. Contains all contexts, entities, metrics, and access policies.
    """

    sdl_version: str = Field(default="1.0", description="SDL language version")
    tenant: str | None = Field(default=None, description="Tenant slug")
    ontology_module: str | None = Field(default=None, description="Primary industry ontology module")
    contexts: list[ContextDefinition] = Field(default_factory=list)
    entities: list[EntityDefinition] = Field(default_factory=list)
    metrics: list[MetricDefinition] = Field(default_factory=list)
    access_policies: list[AccessPolicyDefinition] = Field(default_factory=list)

    @field_validator("ontology_module")
    @classmethod
    def ontology_module_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_ONTOLOGY_MODULES:
            raise ValueError(
                f"ontology_module must be one of {sorted(VALID_ONTOLOGY_MODULES)}, got: {v!r}"
            )
        return v

    @model_validator(mode="after")
    def entity_names_unique(self) -> "SDLDocument":
        names = [e.name for e in self.entities]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate entity names: {duplicates}")
        return self

    @model_validator(mode="after")
    def metric_names_unique(self) -> "SDLDocument":
        names = [m.name for m in self.metrics]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate metric names: {duplicates}")
        return self

    @model_validator(mode="after")
    def context_names_unique(self) -> "SDLDocument":
        names = [c.name for c in self.contexts]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate context names: {names}")
        return self

    @model_validator(mode="after")
    def access_policy_names_unique(self) -> "SDLDocument":
        names = [p.name for p in self.access_policies]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate access policy names: {names}")
        return self

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "SDLDocument":
        """Parse an SDL YAML string into a validated SDLDocument."""
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            raise ValueError("SDL YAML must be a mapping at the top level")
        return cls.model_validate(data)

    def to_yaml(self) -> str:
        """Serialize this document back to YAML."""
        return yaml.dump(
            self.model_dump(exclude_none=True, exclude_defaults=False),
            allow_unicode=True,
            sort_keys=False,
        )

    @property
    def context_names(self) -> set[str]:
        return {c.name for c in self.contexts}

    @property
    def entity_names(self) -> set[str]:
        return {e.name for e in self.entities}

    @property
    def access_policy_names(self) -> set[str]:
        return {p.name for p in self.access_policies}
