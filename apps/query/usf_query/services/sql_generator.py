from __future__ import annotations
from typing import Any
import sqlglot
from loguru import logger

_DIALECT_MAP = {"postgres": "postgres", "snowflake": "snowflake", "bigquery": "bigquery"}
_AGG_MAP = {"sum": "SUM", "count": "COUNT", "avg": "AVG", "min": "MIN", "max": "MAX"}


def generate_metric_sql(
    metric: dict[str, Any],
    context: str,
    dialect: str = "postgres",
    dimensions: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    time_grain: str | None = None,
) -> str:
    metric_name = metric.get("name", "metric")
    metric_type = metric.get("type", "sum").lower()
    measure = metric.get("measure", "amount")
    dims = dimensions or metric.get("dimensions", [])
    ctx_cfg = metric.get("contexts", {}).get(context, {})
    base_filter = ctx_cfg.get("filter", "")
    table = ctx_cfg.get("table", metric.get("table", "facts"))

    agg = _AGG_MAP.get(metric_type, "SUM")
    agg_expr = f"{agg}({measure}) AS {metric_name}"

    select_parts = list(dims) + [agg_expr]
    if time_grain and time_grain in (metric.get("time_grains") or []):
        select_parts = [f"DATE_TRUNC(\'{time_grain}\', event_date) AS period"] + select_parts

    where_parts = []
    if base_filter:
        where_parts.append(f"({base_filter})")
    if filters:
        for col, val in filters.items():
            if isinstance(val, str):
                where_parts.append(f"{col} = \'{val}\'")
            elif isinstance(val, (int, float)):
                where_parts.append(f"{col} = {val}")
            elif isinstance(val, list):
                vals_str = ", ".join(f"\'{v}\'" if isinstance(v, str) else str(v) for v in val)
                where_parts.append(f"{col} IN ({vals_str})")

    parts = [f"SELECT {', '.join(select_parts)}", f"FROM {table}"]
    if where_parts:
        parts.append(f"WHERE {' AND '.join(where_parts)}")
    if dims:
        parts.append(f"GROUP BY {', '.join(str(i+1) for i in range(len(dims)))}")

    raw_sql = "\n".join(parts)
    try:
        return sqlglot.transpile(raw_sql, read="postgres", write=_DIALECT_MAP.get(dialect, "postgres"))[0]
    except Exception as exc:
        logger.warning("SQLGlot transpile failed, using raw SQL", error=str(exc))
        return raw_sql
