from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "usf-mcp"
    usf_api_url: str = "http://usf-api:8000"
    service_token: str = ""  # Service-to-service JWT or API key
    mcp_port: int = 8005


settings = Settings()
