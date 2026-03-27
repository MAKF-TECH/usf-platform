"""SQL compiler — SDL metric → SQL using SQLGlot."""
from __future__ import annotations

from typing import Any

import sqlglot
import sqlglot.expressions as exp

SUPPORTED_DIALECTS = ("snowflake", "postgres", "bigquery", "duckdb")


def compile_metric_to_sql(metric: dict, entity_map: dict[str, str], dialect: str = "snowflake") -> str:
    """
    Compile a USF SDL metric definition to SQL for the given dialect.
    entity_map: {EntityName: "table_name"}
    Returns SQL string.
    """
    if dialect not in SUPPORTED_DIALECTS:
        raise ValueError(f"Unsupported dialect: {dialect}. Choose from {SUPPORTED_DIALECTS}")

    # Use sql_hint if provided
    hints = metric.get("sql_hint", {})
    if dialect in hints:
        # Transpile the hint SQL to target dialect (normalise from snowflake)
        raw_sql = hints[dialect]
        try:
            return sqlglot.transpile(raw_sql, read="snowflake", write=dialect, pretty=True)[0]
        except Exception:
            return raw_sql  # return as-is if transpile fails

    entity_name = metric.get("entity", "")
    table = entity_map.get(entity_name, entity_name.lower())
    agg = metric.get("aggregation", "SUM")
    field = metric.get("field", "value")
    group_fields = metric.get("group_by", [])
    filters = metric.get("filters", [])

    # Build SQL using sqlglot AST
    select_exprs = [exp.Anonymous(this=f"{agg}({table}.{field})", expressions=[]) ]
    group_cols = []
    for gf in group_fields:
        col_expr = _resolve_field_ref(gf, table)
        select_exprs.insert(0, sqlglot.parse_one(col_expr))
        group_cols.append(col_expr)

    from_clause = f"FROM {table}"
    where_parts = []
    for f in filters:
        fname = f.get("field", "")
        op = f.get("operator", "=")
        val = f.get("value")
        if op == "IN" and isinstance(val, list):
            vals = ", ".join(f"'{v}'" for v in val)
            where_parts.append(f"{table}.{fname} IN ({vals})")
        else:
            where_parts.append(f"{table}.{fname} {op} '{val}'")

    parts = [
        f"SELECT {', '.join([str(e) for e in select_exprs])}",
        from_clause,
    ]
    if where_parts:
        parts.append(f"WHERE {' AND '.join(where_parts)}")
    if group_cols:
        parts.append(f"GROUP BY {', '.join(group_cols)}")
        parts.append(f"ORDER BY {agg}({table}.{field}) DESC")

    raw_sql = "\n".join(parts)
    try:
        return sqlglot.transpile(raw_sql, read="snowflake", write=dialect, pretty=True)[0]
    except Exception:
        return raw_sql


def _resolve_field_ref(field_ref: str, default_table: str) -> str:
    """Convert 'entity.field' notation to 'join_alias.column'."""
    if "." in field_ref:
        entity, field = field_ref.split(".", 1)
        alias = entity.lower()
        return f"{alias}.{field.replace('.', '_')}"
    return f"{default_table}.{field_ref}"


def compile_all_dialects(metric: dict, entity_map: dict[str, str]) -> dict[str, str]:
    """Compile metric to all supported dialects."""
    result = {}
    for dialect in SUPPORTED_DIALECTS:
        try:
            result[dialect] = compile_metric_to_sql(metric, entity_map, dialect)
        except Exception as exc:
            result[dialect] = f"-- ERROR: {exc}"
    return result
