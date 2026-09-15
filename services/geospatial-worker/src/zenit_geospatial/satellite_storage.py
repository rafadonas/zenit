"""Encrypted local object storage for provider raster assets."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urlsplit

from Crypto.Cipher import AES
from minio import Minio
from minio.error import S3Error
from minio.versioningconfig import ENABLED, VersioningConfig

from zenit_api.config import Settings


class SatelliteContentMismatchError(RuntimeError):
    """Raised when a deterministic object key already contains different content."""


@dataclass(frozen=True, slots=True)
class StoredSatelliteAsset:
    bucket: str
    object_name: str
    version_id: str
    storage_uri: str


class EncryptedSatelliteStore:
    """Store verified provider bytes encrypted at rest with versioning enabled."""

    def __init__(self, settings: Settings) -> None:
        endpoint = urlsplit(settings.object_storage_endpoint)
        if endpoint.scheme not in {"http", "https"} or not endpoint.netloc:
            raise ValueError("OBJECT_STORAGE_ENDPOINT must be an HTTP(S) URL")
        key = base64.b64decode(
            settings.object_storage_media_encryption_key.get_secret_value(),
            validate=True,
        )
        if len(key) != 32:
            raise ValueError("OBJECT_STORAGE_MEDIA_ENCRYPTION_KEY must decode to 32 bytes")
        self._client = Minio(
            endpoint.netloc,
            access_key=settings.object_storage_access_key,
            secret_key=settings.object_storage_secret_key.get_secret_value(),
            secure=endpoint.scheme == "https",
        )
        self._bucket = settings.object_storage_bucket_raw
        self._encryption_key = key

    def put_verified(
        self,
        *,
        order_id: str,
        scene_id: str,
        asset_role: str,
        content: bytes,
        media_type: str,
        checksum_sha256: str,
    ) -> StoredSatelliteAsset:
        if hashlib.sha256(content).hexdigest() != checksum_sha256:
            raise SatelliteContentMismatchError("download checksum mismatch")
        if not content:
            raise SatelliteContentMismatchError("downloaded asset is empty")
        object_name = (
            f"planet/orders/{_safe(order_id)}/{_safe(scene_id)}/"
            f"{_safe(asset_role)}/{checksum_sha256}.aesgcm"
        )
        self._ensure_bucket()
        try:
            existing = self._client.stat_object(self._bucket, object_name)
        except S3Error as error:
            if error.code not in {"NoSuchKey", "NoSuchObject"}:
                raise
        else:
            metadata = {key.lower(): value for key, value in (existing.metadata or {}).items()}
            if (
                metadata.get("x-amz-meta-plaintext-sha256") != checksum_sha256
                or metadata.get("x-amz-meta-plaintext-size") != str(len(content))
                or metadata.get("x-amz-meta-original-media-type") != media_type
                or metadata.get("x-amz-meta-encryption-method") != "APP-AES256-GCM"
                or not existing.version_id
            ):
                raise SatelliteContentMismatchError("existing encrypted object metadata mismatch")
            return StoredSatelliteAsset(
                bucket=self._bucket,
                object_name=object_name,
                version_id=existing.version_id,
                storage_uri=f"s3://{self._bucket}/{object_name}",
            )

        cipher = AES.new(self._encryption_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(content)
        encrypted = cipher.nonce + tag + ciphertext
        result = self._client.put_object(
            self._bucket,
            object_name,
            BytesIO(encrypted),
            len(encrypted),
            content_type="application/octet-stream",
            metadata={
                "plaintext-sha256": checksum_sha256,
                "plaintext-size": str(len(content)),
                "original-media-type": media_type,
                "encryption-method": "APP-AES256-GCM",
                "order-id": order_id,
                "scene-id": scene_id,
                "asset-role": asset_role,
                "data-status": "real",
            },
        )
        if not result.version_id:
            raise RuntimeError("versioned object storage returned no version_id")
        return StoredSatelliteAsset(
            bucket=self._bucket,
            object_name=object_name,
            version_id=result.version_id,
            storage_uri=f"s3://{self._bucket}/{object_name}",
        )

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            try:
                self._client.make_bucket(self._bucket)
            except S3Error as error:
                if error.code != "BucketAlreadyOwnedByYou":
                    raise
        self._client.set_bucket_versioning(self._bucket, VersioningConfig(ENABLED))


def _safe(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in value)
    if not safe:
        raise ValueError("storage path component must not be empty")
    return safe[:200]
