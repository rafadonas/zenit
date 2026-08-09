from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
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
    auth_secret_key: SecretStr = SecretStr(
        "development-only-change-this-authentication-secret"
    )
    auth_access_token_minutes: int = Field(default=30, ge=5, le=1440)
    auth_token_issuer: str = "zenit"
    auth_token_audience: str = "zenit-api"
    recommendation_review_policy_version: str = "recommendation-review-mvp-v1"
    inspection_order_policy_version: str = "prepared-inspection-order-v1"
    copernicus_client_id: str | None = None
    copernicus_client_secret: str | None = None
    bdc_access_token: str | None = None

    @model_validator(mode="after")
    def reject_development_auth_secret_outside_safe_environments(self) -> "Settings":
        secret = self.auth_secret_key.get_secret_value()
        if self.app_env in {"staging", "production"} and (
            secret == "development-only-change-this-authentication-secret" or len(secret) < 32
        ):
            raise ValueError(
                "AUTH_SECRET_KEY must be a non-default value of at least 32 characters"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
