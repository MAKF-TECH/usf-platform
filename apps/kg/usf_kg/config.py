from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="USF_KG_", env_file=".env", extra="ignore")

    # QLever SPARQL endpoints
    qlever_url: str = "http://qlever:7001"
    qlever_update_url: str = "http://qlever:7001/update"

    # ArcadeDB
    arcadedb_url: str = "http://arcadedb:2480"
    arcadedb_user: str = "root"
    arcadedb_pass: str = "changeme"
    arcadedb_database: str = "usf"

    # PostgreSQL (for audit log + job state, shared with usf-api)
    database_url: str = "postgresql+psycopg://usf:usf@postgres:5432/usf"

    # SHACL quarantine named graph prefix
    quarantine_graph_prefix: str = "usf://quarantine/"

    # Service name (used in health check)
    service_name: str = "usf-kg"

    # Log level
    log_level: str = "INFO"


settings = Settings()
