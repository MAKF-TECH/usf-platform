"""Pydantic models for dbt schema.yml metric definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DbtFilter(BaseModel):
    """A dbt metric filter clause."""

    field: str
    operator: str
    value: str


class DbtMetric(BaseModel):
    """Represents a single dbt metric definition from schema.yml."""

    name: str
    label: str | None = None
    description: str = ""
    type: str = "sum"  # sum | count | average | count_distinct | derived
    sql: str | None = None
    expression: str | None = None  # for derived metrics
    model: str | None = Field(default=None, alias="model")
    timestamp: str | None = None
    time_grains: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    filters: list[DbtFilter] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}
