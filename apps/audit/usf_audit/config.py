from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://usf:usf@postgres:5432/usf"
    QLEVER_URL: str = "http://qlever:7001"
    REDPANDA_BROKERS: str = "redpanda:9092"
    OPENLINEAGE_TOPIC: str = "openlineage.events"
    SERVICE_NAME: str = "usf-audit"
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
