from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    DATABASE_URL: str = "postgresql+psycopg://usf:usf@postgres:5432/usf"

    # Valkey / Redis
    VALKEY_URL: str = "redis://valkey:6379/0"

    # Redpanda / Kafka
    REDPANDA_BROKERS: str = "redpanda:9092"

    # USF Knowledge Graph SPARQL endpoint
    USF_KG_URL: str = "http://qlever:7001"

    # OpenLineage collector
    OPENLINEAGE_URL: str = "http://marquez:5000"

    # Ontop sidecar
    ONTOP_URL: str = "http://ontop:8080"

    # LLM for schema alignment
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = "gpt-4o"

    # Service meta
    SERVICE_NAME: str = "usf-ingest"
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
