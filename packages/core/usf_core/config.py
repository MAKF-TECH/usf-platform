"""USF Core Settings — pydantic-settings BaseSettings for all services."""
from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class USFBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    SERVICE_NAME: str = "usf-service"
    SERVICE_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development","staging","production"] = "development"
    LOG_LEVEL: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"] = "INFO"
    LOG_JSON: bool = True

    DATABASE_URL: str = "postgresql+psycopg://usf_app:changeme@localhost:5432/usf"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    VALKEY_URL: str = "redis://valkey:6379/0"
    CACHE_TTL_SECONDS: int = 300

    REDPANDA_BOOTSTRAP: str = "redpanda:9092"
    LINEAGE_TOPIC: str = "usf.lineage.events"

    JWT_PUBLIC_KEY_PATH: str = "/run/secrets/jwt_public.pem"
    JWT_PRIVATE_KEY_PATH: str | None = None
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    OPA_URL: str = "http://opa:8181"
    OPA_POLICY_PATH: str = "usf/authz"

    QLEVER_SPARQL_ENDPOINT: str = "http://qlever:7001/sparql"
    QLEVER_UPDATE_ENDPOINT: str = "http://qlever:7001/update"

    ARCADEDB_URL: str = "http://arcadedb:2480"
    ARCADEDB_DATABASE: str = "usf"
    ARCADEDB_USER: str = "root"
    ARCADEDB_PASSWORD: str = "changeme"

    ONTOP_SPARQL_ENDPOINT: str = "http://ontop:8080/sparql"
    WREN_ENGINE_URL: str = "http://wren-engine:8080"

    LLM_PROVIDER: Literal["openai","google","azure_openai"] = "google"
    LLM_MODEL: str = "gemini-1.5-pro"
    OPENAI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None

    GITHUB_APP_ID: str | None = None
    GITHUB_INSTALLATION_ID: str | None = None
    GITHUB_PRIVATE_KEY_PATH: str | None = None
    GITHUB_REPO: str | None = None

    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    OTEL_SERVICE_NAME: str | None = None


class APISettings(USFBaseSettings):
    SERVICE_NAME: str = "usf-api"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:4200"])
    QUERY_SERVICE_URL: str = "http://usf-query:8001"
    KG_SERVICE_URL: str = "http://usf-kg:8002"
    SDL_SERVICE_URL: str = "http://usf-sdl:8003"
    AUDIT_SERVICE_URL: str = "http://usf-audit:8005"


class QuerySettings(USFBaseSettings):
    SERVICE_NAME: str = "usf-query"
    API_PORT: int = 8001
    KG_SERVICE_URL: str = "http://usf-kg:8002"
    NL2SPARQL_MAX_ITERATIONS: int = 3


class KGSettings(USFBaseSettings):
    SERVICE_NAME: str = "usf-kg"
    API_PORT: int = 8002
    SHACL_VALIDATE_DEFAULT: bool = True
    QUARANTINE_ON_VIOLATION: bool = True
    PYOXIGRAPH_STORE_PATH: str = "/data/pyoxigraph"


class IngestSettings(USFBaseSettings):
    SERVICE_NAME: str = "usf-ingest"
    API_PORT: int = 8004
    KG_SERVICE_URL: str = "http://usf-kg:8002"
    CELERY_BROKER_URL: str = "redis://valkey:6379/1"
    DOCLING_DEVICE: Literal["cpu","cuda","mps"] = "cpu"


class SDLSettings(USFBaseSettings):
    SERVICE_NAME: str = "usf-sdl"
    API_PORT: int = 8003
    KG_SERVICE_URL: str = "http://usf-kg:8002"
    SDL_STORAGE_PATH: str = "/data/sdl"


class AuditSettings(USFBaseSettings):
    SERVICE_NAME: str = "usf-audit"
    API_PORT: int = 8005
    AUDIT_RETENTION_YEARS: int = 7
    EXPORT_STORAGE_PATH: str = "/data/audit-exports"


class MCPSettings(USFBaseSettings):
    SERVICE_NAME: str = "usf-mcp"
    MCP_PORT: int = 8006
    API_SERVICE_URL: str = "http://usf-api:8000"
    MCP_TRANSPORT: Literal["sse","stdio"] = "sse"


@lru_cache
def get_api_settings() -> APISettings: return APISettings()

@lru_cache
def get_query_settings() -> QuerySettings: return QuerySettings()

@lru_cache
def get_kg_settings() -> KGSettings: return KGSettings()

@lru_cache
def get_ingest_settings() -> IngestSettings: return IngestSettings()

@lru_cache
def get_sdl_settings() -> SDLSettings: return SDLSettings()

@lru_cache
def get_audit_settings() -> AuditSettings: return AuditSettings()

@lru_cache
def get_mcp_settings() -> MCPSettings: return MCPSettings()
