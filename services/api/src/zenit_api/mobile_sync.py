from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


class MobileDeviceRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: UUID
    platform: Literal["android"]
    app_version: str = Field(min_length=1, max_length=100)

    @field_validator("app_version")
    @classmethod
    def normalize_app_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("app version cannot be blank")
        return normalized


class MobileDeviceRegistrationResponse(BaseModel):
    device_id: UUID
    platform: Literal["android"]
    registered_app_version: str
    registered_at: datetime
    registration_status: Literal["active"] = "active"
    data_status: Literal["prepared"] = "prepared"
    authorizes_field_work: Literal[False] = False


class PreparedMeasurementPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_order_id: UUID
    planned_point_id: UUID
    phase: Literal["inspection"]
    height_cm: Decimal = Field(ge=0, le=1000, max_digits=7, decimal_places=2)
    captured_at: datetime
    data_status: Literal["prepared"]
    eligible_for_official_reporting: Literal[False]
    location_status: Literal["not_collected"]
    photo_status: Literal["not_collected"]

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include a UTC offset")
        return value


class DemoWorkOrderEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_order_id: UUID
    occurred_at: datetime
    data_status: Literal["simulated"]
    simulation_scope: Literal["demo_only"]
    authorizes_field_work: Literal[False]
    eligible_for_official_reporting: Literal[False]
    location_status: Literal["not_collected", "simulated"]
    simulated_latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    simulated_longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    simulation_method: Literal["prepared_point_demo_v1"] | None = None

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a UTC offset")
        return value


class PreparedPhotoManifestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    photo_id: UUID
    work_order_id: UUID
    planned_point_id: UUID
    phase: Literal["inspection"]
    captured_at: datetime
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_size: int = Field(gt=0, le=26_214_400)
    media_type: Literal["image/jpeg", "image/png"]
    content_status: Literal["not_uploaded"]
    ruler_status: Literal["not_validated"]
    location_status: Literal["not_collected"]
    data_status: Literal["prepared"]
    eligible_for_official_reporting: Literal[False]

    @field_validator("captured_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include a UTC offset")
        return value


class MobileSyncEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    entity_type: str = Field(min_length=1, max_length=50, pattern=r"^[a-z_]+$")
    operation: str = Field(min_length=1, max_length=50, pattern=r"^[a-z_]+$")
    payload: dict[str, object]

    @model_validator(mode="after")
    def validate_supported_payload_shape(self) -> MobileSyncEventRequest:
        if len(_canonical_json(self.payload)) > 20_000:
            raise ValueError("event payload exceeds 20000 encoded characters")
        if self.entity_type == "measurement" and self.operation == "create":
            measurement = PreparedMeasurementPayload.model_validate(self.payload)
            self.payload = measurement.model_dump(mode="json")
        if self.entity_type == "work_order" and self.operation in {
            "confirm",
            "start",
            "finish",
        }:
            order_event = DemoWorkOrderEventPayload.model_validate(self.payload)
            has_simulated_location = (
                order_event.location_status == "simulated"
                and order_event.simulated_latitude is not None
                and order_event.simulated_longitude is not None
                and order_event.simulation_method == "prepared_point_demo_v1"
            )
            has_no_location = (
                order_event.location_status == "not_collected"
                and order_event.simulated_latitude is None
                and order_event.simulated_longitude is None
                and order_event.simulation_method is None
            )
            if (self.operation == "start" and not has_simulated_location) or (
                self.operation != "start" and not has_no_location
            ):
                raise ValueError("demo event location does not match its operation")
            self.payload = order_event.model_dump(mode="json")
        if self.entity_type == "photo" and self.operation == "prepare":
            photo = PreparedPhotoManifestPayload.model_validate(self.payload)
            self.payload = photo.model_dump(mode="json")
        return self


class MobileSyncBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: UUID
    batch_id: UUID
    base_sync_cursor: int = Field(ge=0)
    events: list[MobileSyncEventRequest] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_unique_event_ids(self) -> MobileSyncBatchRequest:
        event_ids = [event.event_id for event in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("event_id values must be unique within a batch")
        return self


class AcceptedSyncEventResponse(BaseModel):
    event_id: UUID
    persisted: Literal[True] = True


class RejectedSyncEventResponse(BaseModel):
    event_id: UUID
    code: str
    message: str
    retryable: bool = False


class ConflictingSyncEventResponse(BaseModel):
    event_id: UUID
    code: Literal["event_id_reused"] = "event_id_reused"
    message: str
    persisted_request_hash: str
    incoming_request_hash: str


class MobileSyncBatchResponse(BaseModel):
    batch_id: UUID
    accepted: list[AcceptedSyncEventResponse]
    rejected: list[RejectedSyncEventResponse]
    conflicts: list[ConflictingSyncEventResponse]
    next_sync_cursor: int = Field(ge=1)
    data_status: Literal["prepared"] = "prepared"
    authorizes_field_work: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False


class MobileDeviceOwnershipError(Exception):
    pass


class MobileDeviceRevokedError(Exception):
    pass


class MobileDeviceNotRegisteredError(Exception):
    pass


class MobileSyncBatchConflictError(Exception):
    pass


class MobileSyncCursorAheadError(Exception):
    pass


class MobileSyncWriter(Protocol):
    async def register_device(
        self,
        *,
        actor: AuthenticatedUser,
        request: MobileDeviceRegistrationRequest,
    ) -> MobileDeviceRegistrationResponse: ...

    async def sync_batch(
        self,
        *,
        actor: AuthenticatedUser,
        request: MobileSyncBatchRequest,
    ) -> MobileSyncBatchResponse: ...


class PostgresMobileSyncRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def register_device(
        self,
        *,
        actor: AuthenticatedUser,
        request: MobileDeviceRegistrationRequest,
    ) -> MobileDeviceRegistrationResponse:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await self._lock_key(cursor, f"device:{request.device_id}")
            await cursor.execute(
                """
                SELECT user_id, platform, registered_app_version, registered_at,
                       EXISTS (
                           SELECT 1 FROM mobile_device_revocation revocation
                           WHERE revocation.device_id = device.device_id
                       )
                FROM mobile_device_registration device
                WHERE device_id = %s
                """,
                (request.device_id,),
            )
            existing = await cursor.fetchone()
            if existing is not None:
                if existing[0] != actor.id:
                    raise MobileDeviceOwnershipError
                if existing[4]:
                    raise MobileDeviceRevokedError
                return MobileDeviceRegistrationResponse(
                    device_id=request.device_id,
                    platform=existing[1],
                    registered_app_version=existing[2],
                    registered_at=existing[3],
                )

            await cursor.execute(
                """
                INSERT INTO mobile_device_registration (
                    device_id,
                    user_id,
                    platform,
                    registered_app_version,
                    registration_metadata
                ) VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING registered_at
                """,
                (
                    request.device_id,
                    actor.id,
                    request.platform,
                    request.app_version,
                    _canonical_json(
                        {
                            "device_identifier_source": "client_generated_uuid",
                            "official_device_registry": False,
                            "scope": "prepared_mobile_sync",
                        }
                    ),
                ),
            )
            registered_at = (await cursor.fetchone())[0]
        return MobileDeviceRegistrationResponse(
            device_id=request.device_id,
            platform=request.platform,
            registered_app_version=request.app_version,
            registered_at=registered_at,
        )

    async def sync_batch(
        self,
        *,
        actor: AuthenticatedUser,
        request: MobileSyncBatchRequest,
    ) -> MobileSyncBatchResponse:
        request_payload = request.model_dump(mode="json")
        request_hash = _sha256(request_payload)
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await self._lock_key(cursor, f"batch:{request.batch_id}")
            await self._require_device(cursor, actor.id, request.device_id)
            existing_batch = await self._load_batch(cursor, request.batch_id)
            if existing_batch is not None:
                if existing_batch[:3] != (actor.id, request.device_id, request_hash):
                    raise MobileSyncBatchConflictError
                return MobileSyncBatchResponse.model_validate(existing_batch[3])

            await cursor.execute("SELECT COALESCE(max(sync_cursor), 0) FROM mobile_sync_batch")
            current_cursor = (await cursor.fetchone())[0]
            if request.base_sync_cursor > current_cursor:
                raise MobileSyncCursorAheadError
            await cursor.execute("SELECT nextval('mobile_sync_cursor_seq')")
            next_cursor = (await cursor.fetchone())[0]

            accepted: list[AcceptedSyncEventResponse] = []
            rejected: list[RejectedSyncEventResponse] = []
            conflicts: list[ConflictingSyncEventResponse] = []

            for event_id in sorted(str(event.event_id) for event in request.events):
                await self._lock_key(cursor, f"event:{event_id}")
            photo_ids = sorted(
                {
                    str(event.payload["photo_id"])
                    for event in request.events
                    if event.entity_type == "photo" and event.operation == "prepare"
                }
            )
            for photo_id in photo_ids:
                await self._lock_key(cursor, f"photo:{photo_id}")
            order_ids = sorted(
                {
                    str(event.payload["work_order_id"])
                    for event in request.events
                    if event.entity_type == "work_order"
                    and event.operation in {"confirm", "start", "finish"}
                }
            )
            for order_id in order_ids:
                await self._lock_key(cursor, f"demo-order:{order_id}")

            for event in request.events:
                event_payload = event.model_dump(mode="json")
                event_hash = _sha256(
                    {
                        "actor_user_id": str(actor.id),
                        "device_id": str(request.device_id),
                        "event": event_payload,
                    }
                )
                existing_event = await self._load_event(cursor, event.event_id)
                if existing_event is not None:
                    if existing_event[0] == event_hash:
                        if existing_event[2] == "accepted":
                            accepted.append(AcceptedSyncEventResponse(event_id=event.event_id))
                        else:
                            rejected.append(
                                RejectedSyncEventResponse(
                                    event_id=event.event_id,
                                    code=existing_event[3],
                                    message=existing_event[4],
                                )
                            )
                    else:
                        conflict = ConflictingSyncEventResponse(
                            event_id=event.event_id,
                            message="event_id was already persisted with different content",
                            persisted_request_hash=existing_event[0],
                            incoming_request_hash=event_hash,
                        )
                        conflicts.append(conflict)
                        await cursor.execute(
                            """
                            INSERT INTO mobile_sync_conflict (
                                batch_id,
                                event_id,
                                device_id,
                                actor_user_id,
                                persisted_request_hash,
                                incoming_request_hash,
                                persisted_payload,
                                incoming_payload,
                                conflict_code
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                            """,
                            (
                                request.batch_id,
                                event.event_id,
                                request.device_id,
                                actor.id,
                                existing_event[0],
                                event_hash,
                                _canonical_json(existing_event[1]),
                                _canonical_json(event_payload),
                                conflict.code,
                            ),
                        )
                    continue

                rejection = await self._validate_new_event(cursor, actor.id, event)
                outcome = "rejected" if rejection is not None else "accepted"
                result_code = rejection.code if rejection else "persisted"
                result_message = rejection.message if rejection else "sync event persisted"
                await cursor.execute(
                    """
                    INSERT INTO mobile_sync_event (
                        event_id,
                        first_batch_id,
                        device_id,
                        actor_user_id,
                        entity_type,
                        operation,
                        request_hash,
                        payload,
                        outcome,
                        result_code,
                        result_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    """,
                    (
                        event.event_id,
                        request.batch_id,
                        request.device_id,
                        actor.id,
                        event.entity_type,
                        event.operation,
                        event_hash,
                        _canonical_json(event_payload),
                        outcome,
                        result_code,
                        result_message,
                    ),
                )
                if rejection is not None:
                    rejected.append(rejection)
                    continue

                if event.entity_type == "measurement":
                    measurement = PreparedMeasurementPayload.model_validate(event.payload)
                    await cursor.execute(
                        """
                        INSERT INTO prepared_field_measurement (
                            event_id, work_order_id, planned_point_id, actor_user_id,
                            device_id, phase, height_cm, client_captured_at,
                            measurement_metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            event.event_id,
                            measurement.work_order_id,
                            measurement.planned_point_id,
                            actor.id,
                            request.device_id,
                            measurement.phase,
                            measurement.height_cm,
                            measurement.captured_at,
                            _canonical_json(
                                {
                                    "location_status": measurement.location_status,
                                    "photo_status": measurement.photo_status,
                                    "official_measurement": False,
                                    "source": "mobile_offline_sync",
                                }
                            ),
                        ),
                    )
                elif event.entity_type == "work_order":
                    order_event = DemoWorkOrderEventPayload.model_validate(event.payload)
                    await cursor.execute(
                        """
                        INSERT INTO prepared_work_order_demo_event (
                            event_id, work_order_id, actor_user_id, device_id,
                            operation, client_occurred_at, location_status,
                            simulated_location, simulation_method
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            CASE WHEN %s IS NULL THEN NULL
                                 ELSE ST_SetSRID(ST_MakePoint(%s, %s), 4326) END,
                            %s
                        )
                        """,
                        (
                            event.event_id,
                            order_event.work_order_id,
                            actor.id,
                            request.device_id,
                            event.operation,
                            order_event.occurred_at,
                            order_event.location_status,
                            order_event.simulated_longitude,
                            order_event.simulated_longitude,
                            order_event.simulated_latitude,
                            order_event.simulation_method,
                        ),
                    )
                else:
                    photo = PreparedPhotoManifestPayload.model_validate(event.payload)
                    await cursor.execute(
                        """
                        INSERT INTO prepared_field_photo_manifest (
                            event_id, photo_id, work_order_id, planned_point_id,
                            actor_user_id, device_id, phase, client_captured_at,
                            checksum_sha256, byte_size, media_type
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            event.event_id,
                            photo.photo_id,
                            photo.work_order_id,
                            photo.planned_point_id,
                            actor.id,
                            request.device_id,
                            photo.phase,
                            photo.captured_at,
                            photo.checksum_sha256,
                            photo.byte_size,
                            photo.media_type,
                        ),
                    )
                accepted.append(AcceptedSyncEventResponse(event_id=event.event_id))

            response = MobileSyncBatchResponse(
                batch_id=request.batch_id,
                accepted=accepted,
                rejected=rejected,
                conflicts=conflicts,
                next_sync_cursor=next_cursor,
            )
            await cursor.execute(
                """
                INSERT INTO mobile_sync_batch (
                    batch_id,
                    device_id,
                    actor_user_id,
                    base_sync_cursor,
                    sync_cursor,
                    request_hash,
                    response_payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    request.batch_id,
                    request.device_id,
                    actor.id,
                    request.base_sync_cursor,
                    next_cursor,
                    request_hash,
                    _canonical_json(response.model_dump(mode="json")),
                ),
            )
        return response

    @staticmethod
    async def _lock_key(cursor: psycopg.AsyncCursor[tuple], key: str) -> None:
        await cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (key,),
        )

    @staticmethod
    async def _load_batch(cursor: psycopg.AsyncCursor[tuple], batch_id: UUID) -> tuple | None:
        await cursor.execute(
            """
            SELECT actor_user_id, device_id, request_hash, response_payload
            FROM mobile_sync_batch
            WHERE batch_id = %s
            """,
            (batch_id,),
        )
        return await cursor.fetchone()

    @staticmethod
    async def _load_event(cursor: psycopg.AsyncCursor[tuple], event_id: UUID) -> tuple | None:
        await cursor.execute(
            """
            SELECT request_hash, payload, outcome, result_code, result_message
            FROM mobile_sync_event
            WHERE event_id = %s
            """,
            (event_id,),
        )
        return await cursor.fetchone()

    @staticmethod
    async def _require_device(
        cursor: psycopg.AsyncCursor[tuple], actor_id: UUID, device_id: UUID
    ) -> None:
        await cursor.execute(
            """
            SELECT user_id,
                   EXISTS (
                       SELECT 1 FROM mobile_device_revocation revocation
                       WHERE revocation.device_id = device.device_id
                   )
            FROM mobile_device_registration device
            WHERE device_id = %s
            """,
            (device_id,),
        )
        device = await cursor.fetchone()
        if device is None:
            raise MobileDeviceNotRegisteredError
        if device[0] != actor_id:
            raise MobileDeviceOwnershipError
        if device[1]:
            raise MobileDeviceRevokedError

    @staticmethod
    async def _validate_new_event(
        cursor: psycopg.AsyncCursor[tuple], actor_id: UUID, event: MobileSyncEventRequest
    ) -> RejectedSyncEventResponse | None:
        if event.entity_type == "work_order" and event.operation in {
            "confirm",
            "start",
            "finish",
        }:
            return await PostgresMobileSyncRepository._validate_demo_order_event(
                cursor, actor_id, event
            )
        if event.entity_type == "photo" and event.operation == "prepare":
            return await PostgresMobileSyncRepository._validate_photo_manifest(
                cursor, actor_id, event
            )
        if event.entity_type != "measurement" or event.operation != "create":
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="unsupported_event",
                message="event type is not supported by the prepared sync boundary",
            )
        measurement = PreparedMeasurementPayload.model_validate(event.payload)
        await cursor.execute(
            """
            SELECT
                point.work_order_id,
                order_record.status,
                order_record.data_status,
                order_record.authorizes_field_work,
                order_record.eligible_for_field_execution,
                order_record.eligible_for_official_reporting,
                point.eligible_for_field_execution,
                EXISTS (
                    SELECT 1
                    FROM road_user_role assignment
                    WHERE assignment.user_id = %s
                      AND assignment.road_id = axis.road_id
                      AND assignment.role IN ('manager', 'supervisor')
                      AND assignment.data_status <> 'simulated'
                )
            FROM work_order_planned_point point
            JOIN work_order order_record ON order_record.id = point.work_order_id
            JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            WHERE point.id = %s
            """,
            (actor_id, measurement.planned_point_id),
        )
        target = await cursor.fetchone()
        if target is None:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="planned_point_not_found",
                message="prepared planned point was not found",
            )
        if target[0] != measurement.work_order_id:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="point_order_mismatch",
                message="planned point does not belong to the supplied work order",
            )
        if target[1:7] != ("prepared", "prepared", False, False, False, False):
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="unsupported_order_state",
                message="only non-operational prepared orders accept prepared measurements",
            )
        if not target[7]:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="road_access_denied",
                message="actor no longer has an eligible role for this road",
            )
        return None

    @staticmethod
    async def _validate_photo_manifest(
        cursor: psycopg.AsyncCursor[tuple],
        actor_id: UUID,
        event: MobileSyncEventRequest,
    ) -> RejectedSyncEventResponse | None:
        photo = PreparedPhotoManifestPayload.model_validate(event.payload)
        await cursor.execute(
            "SELECT event_id FROM prepared_field_photo_manifest WHERE photo_id = %s",
            (photo.photo_id,),
        )
        if await cursor.fetchone() is not None:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="photo_id_reused",
                message="photo_id was already persisted by another event",
            )
        await cursor.execute(
            """
            SELECT point.work_order_id, order_record.status, order_record.data_status,
                   order_record.authorizes_field_work,
                   order_record.eligible_for_field_execution,
                   order_record.eligible_for_official_reporting,
                   point.eligible_for_field_execution,
                   EXISTS (
                       SELECT 1 FROM road_user_role assignment
                       WHERE assignment.user_id = %s
                         AND assignment.road_id = axis.road_id
                         AND assignment.role IN ('manager', 'supervisor')
                         AND assignment.data_status <> 'simulated'
                   )
            FROM work_order_planned_point point
            JOIN work_order order_record ON order_record.id = point.work_order_id
            JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            WHERE point.id = %s
            """,
            (actor_id, photo.planned_point_id),
        )
        target = await cursor.fetchone()
        if target is None:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="planned_point_not_found",
                message="prepared planned point was not found",
            )
        if target[0] != photo.work_order_id:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="point_order_mismatch",
                message="planned point does not belong to the supplied work order",
            )
        if target[1:7] != ("prepared", "prepared", False, False, False, False):
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="unsupported_order_state",
                message="photo manifests require a non-operational prepared order",
            )
        if not target[7]:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="road_access_denied",
                message="actor no longer has an eligible role for this road",
            )
        return None

    @staticmethod
    async def _validate_demo_order_event(
        cursor: psycopg.AsyncCursor[tuple],
        actor_id: UUID,
        event: MobileSyncEventRequest,
    ) -> RejectedSyncEventResponse | None:
        order_event = DemoWorkOrderEventPayload.model_validate(event.payload)
        await cursor.execute(
            """
            SELECT order_record.status, order_record.data_status,
                   order_record.authorizes_field_work,
                   order_record.eligible_for_field_execution,
                   order_record.eligible_for_official_reporting,
                   EXISTS (
                       SELECT 1 FROM road_user_role assignment
                       WHERE assignment.user_id = %s
                         AND assignment.road_id = axis.road_id
                         AND assignment.role IN ('manager', 'supervisor')
                         AND assignment.data_status <> 'simulated'
                   )
            FROM work_order order_record
            JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            WHERE order_record.id = %s
            """,
            (actor_id, order_event.work_order_id),
        )
        target = await cursor.fetchone()
        if target is None:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="work_order_not_found",
                message="prepared work order was not found",
            )
        if target[:5] != ("prepared", "prepared", False, False, False):
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="unsupported_order_state",
                message="demo events require a non-operational prepared order",
            )
        if not target[5]:
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="road_access_denied",
                message="actor no longer has an eligible role for this road",
            )
        await cursor.execute(
            """
            SELECT operation
            FROM prepared_work_order_demo_event
            WHERE work_order_id = %s
            """,
            (order_event.work_order_id,),
        )
        operations = {row[0] for row in await cursor.fetchall()}
        required_previous = {"start": "confirm", "finish": "start"}.get(event.operation)
        if (
            event.operation in operations
            or (required_previous is not None and required_previous not in operations)
            or (event.operation == "confirm" and operations)
        ):
            return RejectedSyncEventResponse(
                event_id=event.event_id,
                code="invalid_demo_sequence",
                message="demo order events must follow confirm, start, finish exactly once",
            )
        if event.operation == "finish":
            await cursor.execute(
                """
                SELECT
                    (SELECT count(DISTINCT planned_point_id)
                     FROM prepared_field_measurement
                     WHERE work_order_id = %s),
                    (SELECT count(DISTINCT planned_point_id)
                     FROM prepared_field_photo_manifest
                     WHERE work_order_id = %s)
                """,
                (order_event.work_order_id, order_event.work_order_id),
            )
            measurement_count, photo_count = await cursor.fetchone()
            if measurement_count != 3:
                return RejectedSyncEventResponse(
                    event_id=event.event_id,
                    code="measurements_incomplete",
                    message="finish requires three persisted prepared point measurements",
                )
            if photo_count != 3:
                return RejectedSyncEventResponse(
                    event_id=event.event_id,
                    code="photos_incomplete",
                    message="finish requires three persisted prepared point photo manifests",
                )
        return None


async def get_mobile_sync_repository() -> PostgresMobileSyncRepository:
    return PostgresMobileSyncRepository(get_settings().database_url)


router = APIRouter(tags=["mobile-sync"])


@router.post("/v1/mobile/devices", response_model=MobileDeviceRegistrationResponse)
async def register_mobile_device(
    request: MobileDeviceRegistrationRequest,
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[MobileSyncWriter, Depends(get_mobile_sync_repository)],
) -> MobileDeviceRegistrationResponse:
    try:
        return await writer.register_device(actor=actor, request=request)
    except MobileDeviceOwnershipError:
        raise HTTPException(status_code=409, detail="device_id belongs to another user") from None
    except MobileDeviceRevokedError:
        raise HTTPException(status_code=403, detail="mobile device is revoked") from None


@router.post("/v1/sync/batch", response_model=MobileSyncBatchResponse)
async def synchronize_mobile_batch(
    request: MobileSyncBatchRequest,
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[MobileSyncWriter, Depends(get_mobile_sync_repository)],
) -> MobileSyncBatchResponse:
    try:
        return await writer.sync_batch(actor=actor, request=request)
    except MobileDeviceNotRegisteredError:
        raise HTTPException(status_code=403, detail="mobile device is not registered") from None
    except MobileDeviceOwnershipError:
        raise HTTPException(
            status_code=403, detail="mobile device belongs to another user"
        ) from None
    except MobileDeviceRevokedError:
        raise HTTPException(status_code=403, detail="mobile device is revoked") from None
    except MobileSyncBatchConflictError:
        raise HTTPException(
            status_code=409,
            detail="batch_id was already persisted with different content",
        ) from None
    except MobileSyncCursorAheadError:
        raise HTTPException(
            status_code=409,
            detail="base_sync_cursor is ahead of the server cursor",
        ) from None
