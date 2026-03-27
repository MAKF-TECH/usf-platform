from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    service_name: str = "usf-mcp"
    usf_api_url: str = "http://usf-api:8000"
    service_token: str = ""
    mcp_port: int = 9000


settings = Settings()
