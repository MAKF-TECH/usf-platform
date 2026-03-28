"""Convert dbt metric definitions to USF SDL YAML format."""

from __future__ import annotations

from typing import Any

from usf_dbt.models import DbtMetric

# dbt metric type → USF SDL metric type
TYPE_MAP: dict[str, str] = {
    "sum": "sum",
    "count": "count",
    "average": "avg",
    "count_distinct": "count_distinct",
    "derived": "derived",
}


def dbt_metric_to_sdl(
    metric: DbtMetric,
    ontology_class: str = "rdfs:Resource",
) -> dict[str, Any]:
    """Convert a single dbt metric to USF SDL metric dict.

    Maps:
      dbt.name            → usf.metric.name
      dbt.type            → usf.metric.type  (via TYPE_MAP)
      dbt.sql             → usf.metric.measure / sql_expression
      dbt.dimensions      → usf.metric.dimensions
      dbt.filters         → usf.metric.filter
      dbt.time_grains     → usf.metric.time_grains
    """
    usf_type = TYPE_MAP.get(metric.type, metric.type)

    sdl_metric: dict[str, Any] = {
        "name": metric.name,
        "type": usf_type,
        "description": metric.description,
        "ontology_class": ontology_class,
    }

    if metric.label:
        sdl_metric["label"] = metric.label

    # measure / expression
    if metric.type == "derived" and metric.expression:
        sdl_metric["sql_expression"] = metric.expression
    elif metric.sql:
        sdl_metric["measure"] = metric.sql

    if metric.dimensions:
        sdl_metric["dimensions"] = metric.dimensions

    if metric.filters:
        sdl_metric["filter"] = [
            {"field": f.field, "operator": f.operator, "value": f.value}
            for f in metric.filters
        ]

    if metric.time_grains:
        sdl_metric["time_grains"] = metric.time_grains

    if metric.model:
        sdl_metric["source_model"] = metric.model

    return sdl_metric
