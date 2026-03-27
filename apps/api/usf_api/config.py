from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "usf-api"
    debug: bool = False

    database_url: str = "postgresql+psycopg://usf:usf@postgres:5432/usf"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "RS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30
    jwt_private_key: str = ""
    jwt_public_key: str = ""

    opa_url: str = "http://opa:8181"
    usf_query_url: str = "http://usf-query:8000"
    usf_kg_url: str = "http://usf-kg:8000"
    valkey_url: str = "redis://valkey:6379/0"
    cache_ttl_seconds: int = 300


settings = Settings()
