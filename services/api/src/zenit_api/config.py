import base64
import binascii
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
    prepared_photo_review_policy_version: str = "prepared-photo-review-v1"
    prepared_inspection_summary_policy_version: str = "prepared-inspection-summary-v1"
    prepared_post_inspection_policy_version: str = "prepared-post-inspection-v1"
    object_storage_endpoint: str = "http://minio:9000"
    object_storage_access_key: str = "zenit"
    object_storage_secret_key: SecretStr = SecretStr("change_me")
    object_storage_bucket_media: str = Field(
        default="zenit-media",
        min_length=3,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$",
    )
    object_storage_media_encryption_key: SecretStr = SecretStr(
        "ZGV2ZWxvcG1lbnQtb25seS0zMi1ieXRlLWtleSEhISE="
    )
    copernicus_client_id: str | None = None
    copernicus_client_secret: str | None = None
    bdc_access_token: str | None = None

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        try:
            media_key = base64.b64decode(
                self.object_storage_media_encryption_key.get_secret_value(),
                validate=True,
            )
        except (binascii.Error, ValueError) as error:
            raise ValueError(
                "OBJECT_STORAGE_MEDIA_ENCRYPTION_KEY must be valid base64"
            ) from error
        if len(media_key) != 32:
            raise ValueError(
                "OBJECT_STORAGE_MEDIA_ENCRYPTION_KEY must decode to 32 bytes"
            )

        secret = self.auth_secret_key.get_secret_value()
        if self.app_env in {"staging", "production"} and (
            secret == "development-only-change-this-authentication-secret" or len(secret) < 32
        ):
            raise ValueError(
                "AUTH_SECRET_KEY must be a non-default value of at least 32 characters"
            )
        if self.app_env in {"staging", "production"} and (
            self.object_storage_secret_key.get_secret_value() == "change_me"
            or self.object_storage_media_encryption_key.get_secret_value()
            == "ZGV2ZWxvcG1lbnQtb25seS0zMi1ieXRlLWtleSEhISE="
        ):
            raise ValueError("object storage credentials and media encryption key must be set")
        if self.app_env in {
            "staging",
            "production",
        } and not self.object_storage_endpoint.startswith("https://"):
            raise ValueError("OBJECT_STORAGE_ENDPOINT must use HTTPS outside safe environments")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
