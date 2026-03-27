"""
USF SDL Pydantic v2 Models.
Canonical schema for SDL YAML validation.
"""
from __future__ import annotations
import re
from typing import Any
import yaml
from pydantic import BaseModel, Field, model_validator, field_validator

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
PASCAL_CASE_PATTERN = re.compile(r"^[A-Z][a-zA-Z0-9]{0,63}$")
CURIE_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*:[A-Za-z][A-Za-z0-9_-]*$")

VALID_XSD_TYPES = frozenset(["string","integer","decimal","date","datetime","boolean","anyURI","float"])
VALID_AGGREGATION_TYPES = frozenset(["sum","count","avg","min","max","count_distinct","custom"])
VALID_TIME_GRAINS = frozenset(["day","week","month","quarter","year"])
VALID_CLEARANCE_LEVELS = frozenset(["public","internal","confidential","restricted","top_secret"])
VALID_ONTOLOGY_MODULES = frozenset(["fibo","fhir","iec-cim","rami40","obo","dcat","gs1","sid"])


class ContextPropertyOverride(BaseModel):
    sql_column: str | None = None
    description: str | None = None


class EntityReference(BaseModel):
    entity: str
    property: str


class PropertyDefinition(BaseModel):
    name: str
    ontology_property: str
    sql_column: str | None = None
    type: str | None = None
    nullable: bool = True
    description: str | None = None
    allowed_values: list[str] = Field(default_factory=list)
    contexts: dict[str, ContextPropertyOverride] = Field(default_factory=dict)
    references: EntityReference | None = None

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
            raise ValueError(f"ontology_property must be a CURIE: {v!r}")
        return v

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_XSD_TYPES:
            raise ValueError(f"type must be one of {sorted(VALID_XSD_TYPES)}, got: {v!r}")
        return v

    @model_validator(mode="after")
    def sql_column_or_contexts(self) -> "PropertyDefinition":
        if self.sql_column is None and not self.contexts:
            raise ValueError(f"Property '{self.name}': either sql_column or contexts with sql_column required")
        return self


class ContextEntityOverride(BaseModel):
    description: str | None = None
    sql_table: str | None = None


class DimensionDefinition(BaseModel):
    name: str
    entity: str
    property: str
    ontology_property: str
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
    description: str | None = None
    filter: str | None = None
    additional_dimensions: list[str] = Field(default_factory=list)


class InlineAccessPolicy(BaseModel):
    read: list[str] = Field(default_factory=list)
    write: list[str] = Field(default_factory=list)
    pii: bool = False
    clearance: str = "internal"

    @field_validator("clearance")
    @classmethod
    def clearance_valid(cls, v: str) -> str:
        if v not in VALID_CLEARANCE_LEVELS:
            raise ValueError(f"clearance must be one of {sorted(VALID_CLEARANCE_LEVELS)}")
        return v


class MetricExample(BaseModel):
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ContextDefinition(BaseModel):
    name: str
    description: str
    named_graph_uri: str | None = None
    parent_context: str | None = None
    ontology_scope: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_slug(cls, v: str) -> str:
        if not SLUG_PATTERN.match(v):
            raise ValueError(f"Context name must be a slug: {v!r}")
        return v


class EntityDefinition(BaseModel):
    name: str
    ontology_class: str
    description: str
    sql_table: str | None = None
    sql_schema: str = "public"
    contexts: dict[str, ContextEntityOverride] = Field(default_factory=dict)
    properties: list[PropertyDefinition] = Field(..., min_length=1)
    access_policy: str | InlineAccessPolicy | None = None

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
            raise ValueError(f"Duplicate property names in entity '{self.name}'")
        return self


class MetricDefinition(BaseModel):
    name: str
    ontology_class: str
    description: str
    type: str
    measure: str
    measure_entity: str
    measure_sql: str | None = None
    dimensions: list[DimensionDefinition] = Field(..., min_length=1)
    contexts: dict[str, ContextMetricOverride] = Field(default_factory=dict)
    default_filter: str | None = None
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
            raise ValueError(f"type must be one of {sorted(VALID_AGGREGATION_TYPES)}")
        return v

    @field_validator("time_grains")
    @classmethod
    def time_grains_valid(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_TIME_GRAINS
        if invalid:
            raise ValueError(f"Invalid time_grains: {invalid}")
        return v

    @model_validator(mode="after")
    def time_grain_requires_column(self) -> "MetricDefinition":
        if self.time_grains and not self.time_column:
            raise ValueError(f"Metric '{self.name}': time_column required when time_grains non-empty")
        if self.time_grains and not self.time_entity:
            raise ValueError(f"Metric '{self.name}': time_entity required when time_grains non-empty")
        return self


class AccessPolicyDefinition(BaseModel):
    name: str
    description: str
    read: list[str] = Field(..., min_length=1)
    write: list[str] = Field(default_factory=list)
    pii: bool
    clearance: str
    row_filter: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_slug(cls, v: str) -> str:
        if not SLUG_PATTERN.match(v):
            raise ValueError(f"Policy name must be a slug: {v!r}")
        return v

    @field_validator("clearance")
    @classmethod
    def clearance_valid(cls, v: str) -> str:
        if v not in VALID_CLEARANCE_LEVELS:
            raise ValueError(f"clearance must be one of {sorted(VALID_CLEARANCE_LEVELS)}")
        return v


class SDLDocument(BaseModel):
    sdl_version: str = "1.0"
    tenant: str | None = None
    ontology_module: str | None = None
    contexts: list[ContextDefinition] = Field(default_factory=list)
    entities: list[EntityDefinition] = Field(default_factory=list)
    metrics: list[MetricDefinition] = Field(default_factory=list)
    access_policies: list[AccessPolicyDefinition] = Field(default_factory=list)

    @field_validator("ontology_module")
    @classmethod
    def ontology_module_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_ONTOLOGY_MODULES:
            raise ValueError(f"ontology_module must be one of {sorted(VALID_ONTOLOGY_MODULES)}")
        return v

    @model_validator(mode="after")
    def names_unique(self) -> "SDLDocument":
        for attr, label in [("entities","entity"),("metrics","metric"),("contexts","context"),("access_policies","access policy")]:
            names = [getattr(o,"name") for o in getattr(self,attr)]
            if len(names) != len(set(names)):
                raise ValueError(f"Duplicate {label} names: {names}")
        return self

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "SDLDocument":
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            raise ValueError("SDL YAML must be a mapping at the top level")
        return cls.model_validate(data)

    def to_yaml(self) -> str:
        return yaml.dump(self.model_dump(exclude_none=True), allow_unicode=True, sort_keys=False)

    @property
    def context_names(self) -> set[str]:
        return {c.name for c in self.contexts}

    @property
    def entity_names(self) -> set[str]:
        return {e.name for e in self.entities}

    @property
    def access_policy_names(self) -> set[str]:
        return {p.name for p in self.access_policies}
