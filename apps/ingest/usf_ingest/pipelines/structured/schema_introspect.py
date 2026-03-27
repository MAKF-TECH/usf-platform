from __future__ import annotations

"""Schema introspection for structured PostgreSQL sources.

Reads table schemas, FK relationships, and existing dbt YAML files.
Output feeds the R2RML generator.
"""

from pathlib import Path
from typing import Any

import sqlglot
import yaml
from loguru import logger
from sqlalchemy import create_engine, inspect, text


def introspect_postgres(
    connection_string: str,
    schema: str = "public",
    table_names: list[str] | None = None,
) -> dict[str, Any]:
    """Return {table: {columns, primary_keys, foreign_keys}} for the given schema."""
    # Use sync engine for introspection (one-shot, not in hot path)
    engine = create_engine(connection_string.replace("+asyncpg", "").replace("+psycopg", ""))
    inspector = inspect(engine)

    target_tables = table_names or inspector.get_table_names(schema=schema)
    result: dict[str, Any] = {}

    for table in target_tables:
        try:
            columns = inspector.get_columns(table, schema=schema)
            pk = inspector.get_pk_constraint(table, schema=schema)
            fks = inspector.get_foreign_keys(table, schema=schema)
            result[table] = {
                "columns": [
                    {"name": c["name"], "type": str(c["type"]), "nullable": c.get("nullable", True)}
                    for c in columns
                ],
                "primary_keys": pk.get("constrained_columns", []),
                "foreign_keys": [
                    {
                        "constrained_columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"],
                    }
                    for fk in fks
                ],
            }
        except Exception as exc:
            logger.warning(f"Could not introspect {table}: {exc}")

    engine.dispose()
    return result


def load_dbt_yaml(dbt_model_path: str | Path) -> dict[str, Any]:
    """Load a dbt schema.yml and return the models dict, or empty if not found."""
    path = Path(dbt_model_path)
    if not path.exists():
        return {}
    with open(path) as f:
        raw = yaml.safe_load(f)
    models = {m["name"]: m for m in raw.get("models", [])}
    logger.debug(f"Loaded dbt YAML: {len(models)} models from {path}")
    return models


def infer_column_semantics(
    column_name: str,
    column_type: str,
    dbt_description: str = "",
) -> str:
    """Best-effort semantic hint for a column (used by R2RML generator)."""
    name_lower = column_name.lower()
    type_lower = column_type.lower()

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


# ── Async introspection (for use in async FastAPI endpoints) ──────────────────

async def async_introspect_postgres(
    connection_string: str,
    schema: str = "public",
    table_names: list[str] | None = None,
) -> dict[str, Any]:
    """
    Async wrapper for introspect_postgres.
    Runs the synchronous SQLAlchemy introspection in a thread pool to avoid
    blocking the event loop.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: introspect_postgres(connection_string, schema, table_names),
    )


async def read_dbt_yaml(project_path: str) -> list[dict[str, Any]]:
    """
    Parse dbt schema.yml files from a project directory.
    Returns list of model definitions: {name, description, columns[]}.
    """
    import asyncio
    from pathlib import Path

    p = Path(project_path)

    def _scan() -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        for yml_file in p.rglob("schema.yml"):
            result = load_dbt_yaml(yml_file)
            for name, defn in result.items():
                models.append({
                    "name": name,
                    "description": defn.get("description", ""),
                    "columns": defn.get("columns", []),
                    "source_file": str(yml_file),
                })
        return models

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _scan)
