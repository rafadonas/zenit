from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import Annotated, Literal, Protocol
from urllib.parse import urlsplit
from uuid import UUID

import psycopg
from Crypto.Cipher import AES
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from minio import Minio
from minio.error import S3Error
from minio.versioningconfig import ENABLED, VersioningConfig
from pydantic import BaseModel

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import Settings, get_settings

MAX_PHOTO_BYTES = 26_214_400


class PreparedPhotoUploadResponse(BaseModel):
    photo_id: UUID
    checksum_sha256: str
    byte_size: int
    media_type: Literal["image/jpeg", "image/png"]
    content_status: Literal["uploaded_unverified"] = "uploaded_unverified"
    ruler_status: Literal["not_validated"] = "not_validated"
    quality_status: Literal["prepared_unverified"] = "prepared_unverified"
    data_status: Literal["prepared"] = "prepared"
    eligible_for_official_reporting: Literal[False] = False
    persisted: Literal[True] = True


class PhotoManifestNotFoundError(Exception):
    pass


class PhotoContentMismatchError(Exception):
    pass


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    name: str
    version_id: str
    etag: str


class MediaWriter(Protocol):
    async def upload(
        self,
        *,
        actor: AuthenticatedUser,
        device_id: UUID,
        photo_id: UUID,
        content: bytes,
        media_type: str,
        checksum_sha256: str,
    ) -> PreparedPhotoUploadResponse: ...


class PrivateMediaStore:
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
        self._bucket = settings.object_storage_bucket_media
        self._encryption_key = key

    def put_verified(
        self,
        *,
        photo_id: UUID,
        content: bytes,
        media_type: str,
        checksum_sha256: str,
    ) -> StoredObject:
        if not self._client.bucket_exists(self._bucket):
            try:
                self._client.make_bucket(self._bucket)
            except S3Error as error:
                if error.code != "BucketAlreadyOwnedByYou":
                    raise
        self._client.set_bucket_versioning(self._bucket, VersioningConfig(ENABLED))
        name = f"prepared-photos/{photo_id}/{checksum_sha256}.aesgcm"

        try:
            existing = self._client.stat_object(self._bucket, name)
        except S3Error as error:
            if error.code not in {"NoSuchKey", "NoSuchObject"}:
                raise
        else:
            metadata = {
                key.lower(): value for key, value in (existing.metadata or {}).items()
            }
            if (
                metadata.get("x-amz-meta-plaintext-sha256") != checksum_sha256
                or metadata.get("x-amz-meta-plaintext-size") != str(len(content))
                or metadata.get("x-amz-meta-original-media-type") != media_type
                or metadata.get("x-amz-meta-encryption-method") != "APP-AES256-GCM"
                or not existing.version_id
            ):
                raise PhotoContentMismatchError
            self._verify_existing_object(
                name=name,
                version_id=existing.version_id,
                content=content,
                checksum_sha256=checksum_sha256,
            )
            return StoredObject(
                bucket=self._bucket,
                name=name,
                version_id=existing.version_id,
                etag=existing.etag,
            )

        cipher = AES.new(self._encryption_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(content)
        encrypted = cipher.nonce + tag + ciphertext
        result = self._client.put_object(
            self._bucket,
            name,
            BytesIO(encrypted),
            len(encrypted),
            content_type="application/octet-stream",
            metadata={
                "plaintext-sha256": checksum_sha256,
                "plaintext-size": str(len(content)),
                "original-media-type": media_type,
                "encryption-method": "APP-AES256-GCM",
                "nonce-bytes": str(len(cipher.nonce)),
                "tag-bytes": str(len(tag)),
                "photo-id": str(photo_id),
                "data-status": "prepared",
            },
        )
        if not result.version_id:
            raise RuntimeError("versioned object storage returned no version_id")
        return StoredObject(
            bucket=self._bucket,
            name=name,
            version_id=result.version_id,
            etag=result.etag,
        )

    def _verify_existing_object(
        self,
        *,
        name: str,
        version_id: str,
        content: bytes,
        checksum_sha256: str,
    ) -> None:
        response = self._client.get_object(
            self._bucket,
            name,
            version_id=version_id,
        )
        try:
            encrypted = response.read()
        finally:
            response.close()
            response.release_conn()
        if len(encrypted) < 32:
            raise PhotoContentMismatchError
        nonce, tag, ciphertext = encrypted[:16], encrypted[16:32], encrypted[32:]
        try:
            plaintext = AES.new(
                self._encryption_key,
                AES.MODE_GCM,
                nonce=nonce,
            ).decrypt_and_verify(ciphertext, tag)
        except ValueError as error:
            raise PhotoContentMismatchError from error
        if (
            plaintext != content
            or hashlib.sha256(plaintext).hexdigest() != checksum_sha256
        ):
            raise PhotoContentMismatchError


class PreparedMediaService:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        self._store = PrivateMediaStore(settings)

    async def upload(
        self,
        *,
        actor: AuthenticatedUser,
        device_id: UUID,
        photo_id: UUID,
        content: bytes,
        media_type: str,
        checksum_sha256: str,
    ) -> PreparedPhotoUploadResponse:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"photo-upload:{photo_id}",),
            )
            await cursor.execute(
                """
                SELECT manifest.event_id, manifest.checksum_sha256,
                       manifest.byte_size, manifest.media_type
                FROM prepared_field_photo_manifest manifest
                JOIN work_order order_record ON order_record.id = manifest.work_order_id
                JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis
                  ON axis.id = segment.road_axis_candidate_id
                JOIN mobile_device_registration device
                  ON device.device_id = manifest.device_id
                JOIN app_user actor ON actor.id = manifest.actor_user_id
                WHERE manifest.photo_id = %s
                  AND manifest.actor_user_id = %s
                  AND manifest.device_id = %s
                  AND device.user_id = %s
                  AND actor.status = 'active'
                  AND EXISTS (
                      SELECT 1 FROM road_user_role assignment
                      WHERE assignment.user_id = %s
                        AND assignment.road_id = axis.road_id
                        AND assignment.role IN ('manager', 'supervisor')
                        AND assignment.data_status <> 'simulated'
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM mobile_device_revocation revocation
                      WHERE revocation.device_id = device.device_id
                  )
                """,
                (photo_id, actor.id, device_id, actor.id, actor.id),
            )
            manifest = await cursor.fetchone()
            if manifest is None:
                raise PhotoManifestNotFoundError
            if manifest[1:] != (checksum_sha256, len(content), media_type):
                raise PhotoContentMismatchError

            await cursor.execute(
                """
                SELECT checksum_sha256, byte_size, media_type
                FROM prepared_photo_upload_receipt WHERE photo_id = %s
                """,
                (photo_id,),
            )
            receipt = await cursor.fetchone()
            if receipt is not None:
                if receipt != (checksum_sha256, len(content), media_type):
                    raise PhotoContentMismatchError
                return _response(photo_id, checksum_sha256, len(content), media_type)

            stored = await asyncio.to_thread(
                self._store.put_verified,
                photo_id=photo_id,
                content=content,
                media_type=media_type,
                checksum_sha256=checksum_sha256,
            )
            await cursor.execute(
                """
                INSERT INTO prepared_photo_upload_receipt (
                    photo_id, manifest_event_id, actor_user_id, device_id,
                    object_bucket, object_name, object_version_id, object_etag,
                    checksum_sha256, byte_size, media_type, encryption_method,
                    content_status, ruler_status, quality_status, data_status,
                    eligible_for_official_reporting
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    'APP-AES256-GCM', 'uploaded_unverified', 'not_validated',
                    'prepared_unverified', 'prepared', false
                )
                """,
                (
                    photo_id,
                    manifest[0],
                    actor.id,
                    device_id,
                    stored.bucket,
                    stored.name,
                    stored.version_id,
                    stored.etag,
                    checksum_sha256,
                    len(content),
                    media_type,
                ),
            )
        return _response(photo_id, checksum_sha256, len(content), media_type)


def _response(
    photo_id: UUID,
    checksum_sha256: str,
    byte_size: int,
    media_type: Literal["image/jpeg", "image/png"],
) -> PreparedPhotoUploadResponse:
    return PreparedPhotoUploadResponse(
        photo_id=photo_id,
        checksum_sha256=checksum_sha256,
        byte_size=byte_size,
        media_type=media_type,
    )


async def get_media_writer() -> PreparedMediaService:
    return PreparedMediaService(get_settings())


router = APIRouter(tags=["media"])


@router.post("/v1/media/{photo_id}", response_model=PreparedPhotoUploadResponse)
async def upload_prepared_photo(
    photo_id: UUID,
    file: Annotated[UploadFile, File()],
    device_id: Annotated[UUID, Header(alias="X-Zenit-Device-ID")],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[MediaWriter, Depends(get_media_writer)],
) -> PreparedPhotoUploadResponse:
    media_type = file.content_type or ""
    if media_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="only JPEG and PNG are accepted")
    content = await file.read(MAX_PHOTO_BYTES + 1)
    if not content or len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="photo must be between 1 byte and 25 MiB")
    if not _matches_signature(content, media_type):
        raise HTTPException(status_code=422, detail="photo signature does not match media type")
    checksum = hashlib.sha256(content).hexdigest()
    try:
        return await writer.upload(
            actor=actor,
            device_id=device_id,
            photo_id=photo_id,
            content=content,
            media_type=media_type,
            checksum_sha256=checksum,
        )
    except PhotoManifestNotFoundError:
        raise HTTPException(status_code=404, detail="prepared photo manifest not found") from None
    except PhotoContentMismatchError:
        raise HTTPException(
            status_code=409, detail="photo content does not match manifest"
        ) from None


def _matches_signature(content: bytes, media_type: str) -> bool:
    if media_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    return content.startswith(b"\x89PNG\r\n\x1a\n")
