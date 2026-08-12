from __future__ import annotations

import asyncio
import hashlib
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import Settings, get_settings
from zenit_api.media import (
    MAX_PHOTO_BYTES,
    PhotoContentMismatchError,
    PhotoManifestNotFoundError,
    PrivateMediaStore,
)


class MowingPostServicePhotoUploadResponse(BaseModel):
    photo_id: UUID
    checksum_sha256: str
    byte_size: int
    media_type: Literal["image/jpeg", "image/png"]
    phase: Literal["post_service"] = "post_service"
    photo_scope: Literal["mowing_demo_post_service_only"] = (
        "mowing_demo_post_service_only"
    )
    content_status: Literal["uploaded_unverified"] = "uploaded_unverified"
    ruler_status: Literal["not_validated"] = "not_validated"
    location_status: Literal["not_collected"] = "not_collected"
    quality_status: Literal["simulated_unverified"] = "simulated_unverified"
    data_status: Literal["simulated"] = "simulated"
    operational_approval_satisfied: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    persisted: Literal[True] = True


class MowingMediaWriter(Protocol):
    async def upload(
        self,
        *,
        actor: AuthenticatedUser,
        device_id: UUID,
        photo_id: UUID,
        content: bytes,
        media_type: str,
        checksum_sha256: str,
    ) -> MowingPostServicePhotoUploadResponse: ...


class MowingPostServiceMediaService:
    def __init__(
        self,
        settings: Settings,
        *,
        store: PrivateMediaStore | None = None,
    ) -> None:
        self._database_url = settings.database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        self._store = store or PrivateMediaStore(settings)

    async def upload(
        self,
        *,
        actor: AuthenticatedUser,
        device_id: UUID,
        photo_id: UUID,
        content: bytes,
        media_type: str,
        checksum_sha256: str,
    ) -> MowingPostServicePhotoUploadResponse:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"mowing-photo-upload:{photo_id}",),
            )
            await cursor.execute(
                """
                SELECT manifest.event_id, manifest.checksum_sha256,
                       manifest.byte_size, manifest.media_type
                FROM prepared_mowing_post_service_photo_manifest manifest
                JOIN prepared_mowing_order mowing
                  ON mowing.id = manifest.mowing_order_id
                JOIN work_order inspection
                  ON inspection.id = mowing.source_inspection_work_order_id
                JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis
                  ON axis.id = segment.road_axis_candidate_id
                JOIN mobile_device_registration device
                  ON device.device_id = manifest.device_id
                JOIN app_user manifest_actor
                  ON manifest_actor.id = manifest.actor_user_id
                WHERE manifest.photo_id = %s
                  AND manifest.actor_user_id = %s
                  AND manifest.device_id = %s
                  AND manifest.phase = 'post_service'
                  AND manifest.photo_scope = 'mowing_demo_post_service_only'
                  AND manifest.content_status = 'not_uploaded'
                  AND manifest.ruler_status = 'not_validated'
                  AND manifest.location_status = 'not_collected'
                  AND manifest.quality_status = 'simulated_unverified'
                  AND manifest.data_status = 'simulated'
                  AND NOT manifest.operational_approval_satisfied
                  AND NOT manifest.authorizes_field_work
                  AND NOT manifest.eligible_for_field_execution
                  AND NOT manifest.eligible_for_model_training
                  AND NOT manifest.eligible_for_official_reporting
                  AND device.user_id = %s
                  AND manifest_actor.status = 'active'
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
                SELECT object_name, object_version_id,
                       checksum_sha256, byte_size, media_type
                FROM prepared_mowing_post_service_photo_upload_receipt
                WHERE photo_id = %s
                """,
                (photo_id,),
            )
            receipt = await cursor.fetchone()
            if receipt is not None:
                if receipt[2:] != (checksum_sha256, len(content), media_type):
                    raise PhotoContentMismatchError
                persisted_content = await asyncio.to_thread(
                    self._store.get_verified,
                    name=receipt[0],
                    version_id=receipt[1],
                )
                if (
                    persisted_content != content
                    or hashlib.sha256(persisted_content).hexdigest() != checksum_sha256
                ):
                    raise PhotoContentMismatchError
                return _response(photo_id, checksum_sha256, len(content), media_type)

            stored = await asyncio.to_thread(
                self._store.put_verified,
                photo_id=photo_id,
                content=content,
                media_type=media_type,
                checksum_sha256=checksum_sha256,
                object_prefix="simulated-mowing-post-service-photos",
                data_status="simulated",
            )
            await cursor.execute(
                """
                INSERT INTO prepared_mowing_post_service_photo_upload_receipt (
                    photo_id, manifest_event_id, actor_user_id, device_id,
                    object_bucket, object_name, object_version_id, object_etag,
                    checksum_sha256, byte_size, media_type, encryption_method
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    'APP-AES256-GCM'
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
) -> MowingPostServicePhotoUploadResponse:
    return MowingPostServicePhotoUploadResponse(
        photo_id=photo_id,
        checksum_sha256=checksum_sha256,
        byte_size=byte_size,
        media_type=media_type,
    )


async def get_mowing_media_writer() -> MowingPostServiceMediaService:
    return MowingPostServiceMediaService(get_settings())


router = APIRouter(tags=["mowing-media"])


@router.post(
    "/v1/mowing-media/{photo_id}",
    response_model=MowingPostServicePhotoUploadResponse,
)
async def upload_mowing_post_service_photo(
    photo_id: UUID,
    file: Annotated[UploadFile, File()],
    device_id: Annotated[UUID, Header(alias="X-Zenit-Device-ID")],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[MowingMediaWriter, Depends(get_mowing_media_writer)],
) -> MowingPostServicePhotoUploadResponse:
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
        raise HTTPException(
            status_code=404,
            detail="simulated post-service photo manifest not found",
        ) from None
    except PhotoContentMismatchError:
        raise HTTPException(
            status_code=409,
            detail="photo content does not match post-service manifest",
        ) from None


def _matches_signature(content: bytes, media_type: str) -> bool:
    if media_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    return content.startswith(b"\x89PNG\r\n\x1a\n")
