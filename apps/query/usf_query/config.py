from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Service identity
    service_name: str = "usf-query"
    debug: bool = False

    # Query backends
    qlever_url: str = "http://qlever:7001"
    arcadedb_url: str = "http://arcadedb:2480"
    wren_engine_url: str = "http://wren-engine:8080"
    ontop_url: str = "http://ontop:8090"

    # Knowledge graph
    usf_kg_url: str = "http://usf-kg:8000"

    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # NL2SPARQL
    nl2sparql_max_iterations: int = 3

    # ArcadeDB auth
    arcadedb_username: str = "root"
    arcadedb_password: str = "arcadedb"
    arcadedb_database: str = "usf"


settings = Settings()
