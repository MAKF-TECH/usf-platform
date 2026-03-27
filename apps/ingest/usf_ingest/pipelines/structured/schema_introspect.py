from __future__ import annotations

"""Schema introspection for PostgreSQL sources."""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from sqlalchemy import create_engine, inspect


def introspect_postgres(connection_string: str, schema: str = "public", table_names: list[str] | None = None) -> dict[str, Any]:
    engine = create_engine(connection_string.replace("+asyncpg", "").replace("+psycopg", ""))
    inspector = inspect(engine)
    target_tables = table_names or inspector.get_table_names(schema=schema)
    result: dict[str, Any] = {}
    for table in target_tables:
        try:
            result[table] = {
                "columns": [{"name": c["name"], "type": str(c["type"]), "nullable": c.get("nullable", True)} for c in inspector.get_columns(table, schema=schema)],
                "primary_keys": inspector.get_pk_constraint(table, schema=schema).get("constrained_columns", []),
                "foreign_keys": [{"constrained_columns": fk["constrained_columns"], "referred_table": fk["referred_table"], "referred_columns": fk["referred_columns"]} for fk in inspector.get_foreign_keys(table, schema=schema)],
            }
        except Exception as exc:
            logger.warning(f"Could not introspect {table}: {exc}")
    engine.dispose()
    return result


def load_dbt_yaml(dbt_model_path: str | Path) -> dict[str, Any]:
    path = Path(dbt_model_path)
    if not path.exists():
        return {}
    with open(path) as f:
        raw = yaml.safe_load(f)
    return {m["name"]: m for m in raw.get("models", [])}


def infer_column_semantics(column_name: str, column_type: str, dbt_description: str = "") -> str:
    name_lower = column_name.lower()
    if any(k in name_lower for k in ("amount", "price", "cost", "value")):
        return "monetary_amount"
    if any(k in name_lower for k in ("date", "time", "timestamp", "created_at", "updated_at")):
        return "temporal"
    if any(k in name_lower for k in ("currency", "ccy")):
        return "currency_code"
    if any(k in name_lower for k in ("bank", "institution", "lender")):
        return "financial_institution"
    if any(k in name_lower for k in ("account", "acct")):
        return "account_identifier"
    if any(k in name_lower for k in ("is_", "has_", "flag", "suspicious", "laundering")):
        return "boolean_flag"
    return "generic"
