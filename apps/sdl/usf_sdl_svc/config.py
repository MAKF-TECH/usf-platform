from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="USF_SDL_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://usf:usf@postgres:5432/usf"
    service_name: str = "usf-sdl"
    log_level: str = "INFO"

    # Default SQL dialect for compilation
    default_sql_dialect: str = "snowflake"


settings = Settings()
