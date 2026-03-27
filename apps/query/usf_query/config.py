from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "usf-query"
    debug: bool = False

    qlever_url: str = "http://qlever:7001"
    arcadedb_url: str = "http://arcadedb:2480"
    wren_engine_url: str = "http://wren-engine:8080"
    ontop_url: str = "http://ontop:8090"
    usf_kg_url: str = "http://usf-kg:8000"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    nl2sparql_max_iterations: int = 3

    arcadedb_username: str = "root"
    arcadedb_password: str = "arcadedb"
    arcadedb_database: str = "usf"


settings = Settings()
