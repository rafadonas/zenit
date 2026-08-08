from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "demo", "staging", "production"] = "development"
    app_name: str = "zenit"
    app_version: str = "0.1.0"
    database_url: str = "postgresql://zenit:change_me@postgres:5432/zenit"
    copernicus_client_id: str | None = None
    copernicus_client_secret: str | None = None
    bdc_access_token: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
