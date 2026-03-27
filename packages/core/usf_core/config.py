"""
USF Core — Settings and environment variable configuration.

All services import from here. No service should define its own settings class
for shared configuration. Service-specific settings extend USFBaseSettings.

Pattern: pydantic-settings BaseSettings with environment variable binding.
All settings are read from environment variables (12-factor app).
Secrets are read from environment or secret files (Docker/K8s secrets).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, PostgresDsn, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class USFBaseSettings(BaseSettings):
    """
    Base settings shared across all USF services.
    Each service should subclass this and add service-specific settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Service identity ───────────────────────────────────────────
    SERVICE_NAME: str = Field(default="usf-service", description="Service name (set per service)")
    SERVICE_VERSION: str = Field(default="0.1.0")
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(default="development")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    LOG_JSON: bool = Field(default=True, description="Use JSON structured logging")

    # ── Database (PostgreSQL / Neon) ───────────────────────────────
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+psycopg://usf_app:changeme@localhost:5432/usf",
        description="Async PostgreSQL DSN (psycopg v3 async driver)",
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)

    # ── Cache (Valkey / Redis) ─────────────────────────────────────
    VALKEY_URL: str = Field(default="redis://valkey:6379/0")
    CACHE_TTL_SECONDS: int = Field(default=300, description="Default query cache TTL (5 min)")

    # ── Message bus (Redpanda / Kafka) ─────────────────────────────
    REDPANDA_BOOTSTRAP: str = Field(
        default="redpanda:9092",
        description="Comma-separated Redpanda bootstrap servers",
    )
    LINEAGE_TOPIC: str = Field(default="usf.lineage.events")

    # ── Authentication (JWT RS256) ─────────────────────────────────
    JWT_PUBLIC_KEY_PATH: str = Field(
        default="/run/secrets/jwt_public_key",
        description="Path to RSA public key PEM file for JWT verification",
    )
    JWT_PRIVATE_KEY_PATH: str | None = Field(
        default=None,
        description="Path to RSA private key PEM for JWT signing (usf-api only)",
    )
    JWT_ALGORITHM: str = Field(default="RS256")
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = Field(default=3600)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

    # ── OPA (authorization sidecar) ────────────────────────────────
    OPA_URL: str = Field(default="http://opa:8181", description="OPA sidecar base URL")
    OPA_POLICY_PATH: str = Field(default="usf/authz", description="OPA policy document path")

    # ── QLever (RDF triplestore) ───────────────────────────────────
    QLEVER_SPARQL_ENDPOINT: str = Field(default="http://qlever:7001/sparql")
    QLEVER_UPDATE_ENDPOINT: str = Field(default="http://qlever:7001/update")

    # ── ArcadeDB (property graph) ──────────────────────────────────
    ARCADEDB_URL: str = Field(default="http://arcadedb:2480")
    ARCADEDB_DATABASE: str = Field(default="usf")
    ARCADEDB_USER: str = Field(default="root")
    ARCADEDB_PASSWORD: str = Field(default="changeme")

    # ── Ontop (SPARQL-SQL virtual KG) ─────────────────────────────
    ONTOP_SPARQL_ENDPOINT: str = Field(default="http://ontop:8080/sparql")

    # ── Wren Engine (semantic SQL) ─────────────────────────────────
    WREN_ENGINE_URL: str = Field(default="http://wren-engine:8080")

    # ── LLM provider ──────────────────────────────────────────────
    LLM_PROVIDER: Literal["openai", "google", "azure_openai"] = Field(default="google")
    LLM_MODEL: str = Field(default="gemini-1.5-pro")
    OPENAI_API_KEY: str | None = Field(default=None)
    GOOGLE_API_KEY: str | None = Field(default=None)
    AZURE_OPENAI_ENDPOINT: str | None = Field(default=None)
    AZURE_OPENAI_KEY: str | None = Field(default=None)

    # ── GitHub App (optional, for SDL git integration) ─────────────
    GITHUB_APP_ID: str | None = Field(default=None)
    GITHUB_INSTALLATION_ID: str | None = Field(default=None)
    GITHUB_PRIVATE_KEY_PATH: str | None = Field(default=None)
    GITHUB_REPO: str | None = Field(
        default=None, description="GitHub repo for SDL version storage: owner/repo"
    )

    # ── Observability ─────────────────────────────────────────────
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = Field(
        default=None, description="OpenTelemetry OTLP gRPC endpoint"
    )
    OTEL_SERVICE_NAME: str | None = Field(default=None, description="Defaults to SERVICE_NAME")


class APISettings(USFBaseSettings):
    """Settings for usf-api."""

    SERVICE_NAME: str = "usf-api"
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_WORKERS: int = Field(default=4)
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:4200"],
        description="Allowed CORS origins",
    )

    # Service URLs (internal)
    QUERY_SERVICE_URL: str = Field(default="http://usf-query:8001")
    KG_SERVICE_URL: str = Field(default="http://usf-kg:8002")
    SDL_SERVICE_URL: str = Field(default="http://usf-sdl:8003")
    AUDIT_SERVICE_URL: str = Field(default="http://usf-audit:8005")


class QuerySettings(USFBaseSettings):
    """Settings for usf-query."""

    SERVICE_NAME: str = "usf-query"
    API_PORT: int = Field(default=8001)
    KG_SERVICE_URL: str = Field(default="http://usf-kg:8002")
    SDL_SERVICE_URL: str = Field(default="http://usf-sdl:8003")
    NL2SPARQL_MAX_ITERATIONS: int = Field(default=3)
    OGRAG_TOP_K_CHUNKS: int = Field(default=5)


class KGSettings(USFBaseSettings):
    """Settings for usf-kg."""

    SERVICE_NAME: str = "usf-kg"
    API_PORT: int = Field(default=8002)
    SDL_SERVICE_URL: str = Field(default="http://usf-sdl:8003")
    SHACL_VALIDATE_DEFAULT: bool = Field(default=True)
    QUARANTINE_ON_VIOLATION: bool = Field(default=True)
    PYOXIGRAPH_STORE_PATH: str = Field(
        default="/data/pyoxigraph",
        description="Path for embedded pyoxigraph store (dev/test only)",
    )


class IngestSettings(USFBaseSettings):
    """Settings for usf-ingest."""

    SERVICE_NAME: str = "usf-ingest"
    API_PORT: int = Field(default=8004)
    KG_SERVICE_URL: str = Field(default="http://usf-kg:8002")
    SDL_SERVICE_URL: str = Field(default="http://usf-sdl:8003")
    CELERY_BROKER_URL: str = Field(default="redis://valkey:6379/1")
    CELERY_RESULT_BACKEND: str = Field(
        default="db+postgresql+psycopg://usf_app:changeme@postgres:5432/usf"
    )
    DOCLING_DEVICE: Literal["cpu", "cuda", "mps"] = Field(default="cpu")


class SDLSettings(USFBaseSettings):
    """Settings for usf-sdl."""

    SERVICE_NAME: str = "usf-sdl"
    API_PORT: int = Field(default=8003)
    KG_SERVICE_URL: str = Field(default="http://usf-kg:8002")
    SDL_STORAGE_PATH: str = Field(
        default="/data/sdl",
        description="Local path for SDL YAML version storage",
    )


class AuditSettings(USFBaseSettings):
    """Settings for usf-audit."""

    SERVICE_NAME: str = "usf-audit"
    API_PORT: int = Field(default=8005)
    AUDIT_RETENTION_YEARS: int = Field(default=7, description="BCBS 239 retention minimum")
    EXPORT_STORAGE_PATH: str = Field(default="/data/audit-exports")


class MCPSettings(USFBaseSettings):
    """Settings for usf-mcp."""

    SERVICE_NAME: str = "usf-mcp"
    MCP_PORT: int = Field(default=8006)
    API_SERVICE_URL: str = Field(default="http://usf-api:8000")
    MCP_TRANSPORT: Literal["sse", "stdio"] = Field(default="sse")


@lru_cache
def get_api_settings() -> APISettings:
    return APISettings()


@lru_cache
def get_query_settings() -> QuerySettings:
    return QuerySettings()


@lru_cache
def get_kg_settings() -> KGSettings:
    return KGSettings()


@lru_cache
def get_ingest_settings() -> IngestSettings:
    return IngestSettings()


@lru_cache
def get_sdl_settings() -> SDLSettings:
    return SDLSettings()


@lru_cache
def get_audit_settings() -> AuditSettings:
    return AuditSettings()


@lru_cache
def get_mcp_settings() -> MCPSettings:
    return MCPSettings()
