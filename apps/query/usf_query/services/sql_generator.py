from __future__ import annotations

from typing import Any

import sqlglot
import sqlglot.expressions as exp
from loguru import logger


# Dialect mapping
_DIALECT_MAP = {
    "postgres": "postgres",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
}

# Type mapping from SDL to SQL
_SDL_TYPE_MAP: dict[str, str] = {
    "string": "VARCHAR",
    "decimal": "DECIMAL(18,4)",
    "integer": "BIGINT",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMP",
    "float": "FLOAT",
}

# Aggregation function mapping
_AGGREGATION_MAP = {
    "sum": "SUM",
    "count": "COUNT",
    "avg": "AVG",
    "min": "MIN",
    "max": "MAX",
    "count_distinct": "COUNT(DISTINCT {measure})",
}


def _get_dialect(dialect: str) -> str:
    return _DIALECT_MAP.get(dialect, "postgres")


def generate_metric_sql(
    metric: dict[str, Any],
    context: str,
    dialect: str = "postgres",
    dimensions: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    time_grain: str | None = None,
) -> str:
    """
    Generate SQL for an SDL metric definition.
    
    metric dict structure (from SDL):
      name, type (sum|count|avg), measure, dimensions, contexts, time_grains
    
    Returns transpiled SQL for the requested dialect.
    """
    metric_name = metric.get("name", "unknown_metric")
    metric_type = metric.get("type", "sum").lower()
    measure = metric.get("measure", "amount")
    all_dimensions: list[str] = dimensions or metric.get("dimensions", [])

    # Context-specific config
    context_config: dict[str, Any] = metric.get("contexts", {}).get(context, {})
    base_filter = context_config.get("filter", "")
    source_table = context_config.get("table", metric.get("table", "facts"))

    # Build aggregation expression
    agg_template = _AGGREGATION_MAP.get(metric_type, "SUM")
    if "{measure}" in agg_template:
        agg_expr = agg_template.format(measure=measure)
    else:
        agg_expr = f"{agg_template}({measure})"

    # Build SELECT clause
    select_parts = list(all_dimensions)
    select_parts.append(f"{agg_expr} AS {metric_name}")

    # Time grain dimension
    if time_grain and time_grain in (metric.get("time_grains") or []):
        time_expr = _time_grain_expr(time_grain, dialect)
        if time_expr:
            select_parts = [time_expr] + select_parts

    # Build WHERE clause
    where_parts = []
    if base_filter:
        where_parts.append(f"({base_filter})")
    if filters:
        for col, val in filters.items():
            if isinstance(val, str):
                where_parts.append(f"{col} = '{val}'")
            elif isinstance(val, (int, float)):
                where_parts.append(f"{col} = {val}")
            elif isinstance(val, list):
                vals_str = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in val)
                where_parts.append(f"{col} IN ({vals_str})")

    # Assemble raw SQL
    sql_parts = [
        f"SELECT {', '.join(select_parts)}",
        f"FROM {source_table}",
    ]
    if where_parts:
        sql_parts.append(f"WHERE {' AND '.join(where_parts)}")
    if all_dimensions:
        sql_parts.append(f"GROUP BY {', '.join(str(i + 1) for i in range(len(all_dimensions)))}")

    raw_sql = "\n".join(sql_parts)

    # Transpile to target dialect using sqlglot
    try:
        transpiled = sqlglot.transpile(raw_sql, read="postgres", write=_get_dialect(dialect))[0]
    except Exception as exc:
        logger.warning(
            "SQLGlot transpilation failed, returning raw SQL",
            error=str(exc),
            metric=metric_name,
        )
        transpiled = raw_sql

    logger.info(
        "SQL generated",
        metric=metric_name,
        context=context,
        dialect=dialect,
        dimensions=all_dimensions,
    )

    return transpiled


def _time_grain_expr(grain: str, dialect: str) -> str | None:
    """Generate time truncation expression for the given grain and dialect."""
    grain_lower = grain.lower()
    if dialect == "snowflake":
        return f"DATE_TRUNC('{grain_lower}', event_date) AS period"
    elif dialect == "bigquery":
        trunc_map = {"day": "DAY", "month": "MONTH", "quarter": "QUARTER", "year": "YEAR"}
        return f"DATE_TRUNC(event_date, {trunc_map.get(grain_lower, grain_lower.upper())}) AS period"
    else:  # postgres
        return f"DATE_TRUNC('{grain_lower}', event_date) AS period"


def compile_metric_sql(
    metric_name: str,
    dimensions: list[str],
    filters: dict,
    time_range: dict,
    context: str,
    dialect: str = "postgres",
) -> str:
    """
    Compile a metric name + dimensions + filters + time_range into warehouse-native SQL.

    This is the public API entry point (per spec). Internally delegates to
    generate_metric_sql with a synthetic metric dict built from the arguments.

    Args:
        metric_name: SDL metric identifier (used as measure column name)
        dimensions:  List of dimension column names to GROUP BY
        filters:     Dict of column→value filters to apply in WHERE clause
        time_range:  Dict with optional keys: start, end, grain
                     e.g. {"start": "2024-01-01", "end": "2024-12-31", "grain": "month"}
        context:     USF context name (determines source table / filter)
        dialect:     Target SQL dialect: postgres | snowflake | bigquery

    Returns:
        Transpiled SQL string ready for the target warehouse.
    """
    time_grain = time_range.get("grain") if time_range else None

    # Build time-range filters
    merged_filters = dict(filters or {})
    if time_range:
        start = time_range.get("start")
        end = time_range.get("end")
        if start:
            merged_filters["event_date >="] = start
        if end:
            merged_filters["event_date <="] = end

    # Handle >= / <= filter operators (not supported by simple generate_metric_sql)
    # We build the WHERE clause manually for range conditions
    range_parts: list[str] = []
    simple_filters: dict = {}
    for k, v in merged_filters.items():
        if k.endswith(" >="):
            col = k[:-3].strip()
            range_parts.append(f"{col} >= '{v}'")
        elif k.endswith(" <="):
            col = k[:-3].strip()
            range_parts.append(f"{col} <= '{v}'")
        else:
            simple_filters[k] = v

    # Synthetic metric dict for generate_metric_sql
    metric_dict: dict = {
        "name": metric_name,
        "type": "sum",
        "measure": metric_name,
        "dimensions": dimensions,
        "table": f"{context}_{metric_name}_facts",
        "contexts": {
            context: {
                "table": f"{context}_{metric_name}_facts",
            }
        },
    }
    if time_grain:
        metric_dict["time_grains"] = [time_grain]

    sql = generate_metric_sql(
        metric=metric_dict,
        context=context,
        dialect=dialect,
        dimensions=dimensions,
        filters=simple_filters,
        time_grain=time_grain,
    )

    # Inject range filters if any
    if range_parts:
        extra_where = " AND ".join(range_parts)
        if "WHERE" in sql.upper():
            # Append to existing WHERE clause (before GROUP BY)
            idx = sql.upper().find("\nGROUP BY")
            if idx != -1:
                sql = sql[:idx] + f"\n  AND {extra_where}" + sql[idx:]
            else:
                sql = sql.rstrip() + f"\n  AND {extra_where}"
        else:
            idx = sql.upper().find("\nGROUP BY")
            if idx != -1:
                sql = sql[:idx] + f"\nWHERE {extra_where}" + sql[idx:]
            else:
                sql = sql.rstrip() + f"\nWHERE {extra_where}"

    logger.info(
        "compile_metric_sql",
        metric=metric_name,
        context=context,
        dialect=dialect,
        dimensions=dimensions,
    )

    return sql
