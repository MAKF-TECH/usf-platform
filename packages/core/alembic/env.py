"""Alembic environment for USF Platform.

Uses SQLModel metadata and psycopg (v3, async-compatible) as the sync driver
for migrations. DATABASE_URL is read from the environment via pydantic-settings.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── USF imports ──────────────────────────────────────────────────────────────
# Import all SQLModel models so their metadata is registered before Alembic
# inspects it.  The import order matters: base models must come first.
from sqlmodel import SQLModel  # noqa: F401

# Import all table models so SQLModel registers them in its metadata.
# Keep this list in sync with usf_core.db_models (or wherever tables live).
try:
    from usf_core.db_models import (  # noqa: F401
        Tenant,
        User,
        RefreshToken,
        DataSource,
        IngestionJob,
        SDLVersion,
        AuditLog,
        JobRun,
        OntologyModule,
        ContextDef,
    )
except ImportError:
    # Fallback: inline minimal metadata so env.py is still runnable even if
    # db_models has not been generated yet.
    pass

# ── Target metadata ───────────────────────────────────────────────────────────
target_metadata = SQLModel.metadata

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

# Interpret the alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Allow DATABASE_URL to be injected from the environment, overriding alembic.ini.
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Alembic needs a sync URL; replace asyncpg/psycopg async drivers with sync.
    sync_url = (
        database_url
        .replace("postgresql+asyncpg://", "postgresql+psycopg://")
        .replace("postgresql+psycopg_async://", "postgresql+psycopg://")
    )
    config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an
    Engine is acceptable here as well.  By skipping the Engine creation we
    don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # USF uses the `usf` schema; tell Alembic to include it.
            include_schemas=True,
            version_table_schema="usf",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
