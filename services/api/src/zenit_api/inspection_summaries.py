from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, ConfigDict, Field, field_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


class PreparedSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generation_rationale: str = Field(min_length=1, max_length=2000)

    @field_validator("generation_rationale")
    @classmethod
    def normalize_rationale(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("generation rationale cannot be blank")
        return normalized


class PreparedSummaryResponse(BaseModel):
    summary_id: UUID
    work_order_id: UUID
    summary_policy_version: str
    generation_rationale: str
    measurement_count: Literal[3]
    accepted_photo_review_count: Literal[3]
    minimum_height_cm: Decimal
    maximum_height_cm: Decimal
    mean_height_cm: Decimal
    n1_count: int
    n2_count: int
    n3_count: int
    class_rule: str = "N1 < 10 cm; N2 10-30 cm; N3 > 30 cm"
    location_status: Literal["simulated"] = "simulated"
    evidence_status: Literal["prepared_reviewed_non_operational"] = (
        "prepared_reviewed_non_operational"
    )
    data_status: Literal["prepared"] = "prepared"
    eligible_for_field_evidence: Literal[False] = False
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    generated_at: datetime


class PreparedSummaryCollection(BaseModel):
    items: list[PreparedSummaryResponse]
    result_count: int
    limit: int
    truncated: bool
    warning: str = (
        "Prepared summaries use simulated demo locations and typed measurements; "
        "they are not official reports and do not authorize field work."
    )


class SummaryTargetNotFoundError(Exception):
    pass


class SummaryPermissionError(Exception):
    pass


class SummaryPolicyUnavailableError(Exception):
    pass


class SummaryEvidenceIncompleteError(Exception):
    pass


class SummaryIdempotencyConflictError(Exception):
    pass


class SummaryAlreadyExistsError(Exception):
    pass


class PreparedSummaryWriter(Protocol):
    async def create(
        self,
        *,
        work_order_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedSummaryRequest,
    ) -> PreparedSummaryResponse: ...


class PreparedSummaryReader(Protocol):
    async def list_for_actor(
        self,
        *,
        actor: AuthenticatedUser,
        limit: int,
    ) -> PreparedSummaryCollection: ...


class PostgresPreparedSummaryRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self,
        *,
        work_order_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedSummaryRequest,
    ) -> PreparedSummaryResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        try:
            async with connection, connection.cursor() as cursor:
                existing = await self._by_key(cursor, key_hash)
                if existing:
                    if (existing[1], existing[2], existing[3]) != (
                        work_order_id,
                        actor.id,
                        request.generation_rationale,
                    ):
                        raise SummaryIdempotencyConflictError
                    return await self._response(cursor, existing[0])
                await cursor.execute(
                    "SELECT 1 FROM prepared_inspection_summary WHERE work_order_id = %s",
                    (work_order_id,),
                )
                if await cursor.fetchone():
                    raise SummaryAlreadyExistsError
                return await self._create(cursor, work_order_id, actor, key_hash, request)
        except UniqueViolation as error:
            if error.diag.constraint_name == "prepared_inspection_summary_work_order_id_key":
                raise SummaryAlreadyExistsError from None
            raise

    async def list_for_actor(
        self,
        *,
        actor: AuthenticatedUser,
        limit: int,
    ) -> PreparedSummaryCollection:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT summary.id, summary.work_order_id, policy.version,
                       summary.generation_rationale, summary.measurement_count,
                       summary.accepted_photo_review_count, summary.minimum_height_cm,
                       summary.maximum_height_cm, summary.mean_height_cm,
                       summary.n1_count, summary.n2_count, summary.n3_count,
                       summary.generated_at
                FROM prepared_inspection_summary summary
                JOIN prepared_inspection_summary_policy policy
                  ON policy.id = summary.summary_policy_id
                JOIN work_order order_record ON order_record.id = summary.work_order_id
                JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis
                  ON axis.id = segment.road_axis_candidate_id
                WHERE summary.location_status = 'simulated'
                  AND summary.data_status = 'prepared'
                  AND NOT summary.eligible_for_official_reporting
                  AND NOT summary.authorizes_field_work
                  AND EXISTS (
                      SELECT 1 FROM road_user_role assignment
                      WHERE assignment.user_id = %s
                        AND assignment.road_id = axis.road_id
                        AND assignment.role IN ('manager', 'supervisor')
                        AND assignment.data_status <> 'simulated'
                  )
                ORDER BY summary.generated_at DESC, summary.id
                LIMIT %s
                """,
                (actor.id, limit + 1),
            )
            rows = await cursor.fetchall()
        truncated = len(rows) > limit
        visible = rows[:limit]
        return PreparedSummaryCollection(
            items=[self._response_from_row(row) for row in visible],
            result_count=len(visible),
            limit=limit,
            truncated=truncated,
        )

    async def _create(self, cursor, work_order_id, actor, key_hash, request):
        await cursor.execute(
            """
                SELECT axis.road_id
                FROM work_order order_record
                JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                WHERE order_record.id = %s AND order_record.status = 'prepared'
                  AND order_record.data_status = 'prepared'
                  AND NOT order_record.authorizes_field_work
                """,
            (work_order_id,),
        )
        target = await cursor.fetchone()
        if not target:
            raise SummaryTargetNotFoundError
        await cursor.execute(
            """SELECT id, version, allowed_roles FROM prepared_inspection_summary_policy
                   WHERE version = %s AND data_status = 'prepared' AND NOT authorizes_field_work""",
            (self._policy_version,),
        )
        policy = await cursor.fetchone()
        if not policy:
            raise SummaryPolicyUnavailableError
        await cursor.execute(
            """SELECT 1 FROM road_user_role WHERE user_id = %s AND road_id = %s
                   AND role = ANY(%s) AND data_status <> 'simulated' LIMIT 1""",
            (actor.id, target[0], policy[2]),
        )
        if not await cursor.fetchone():
            raise SummaryPermissionError
        await cursor.execute(
            """
                SELECT
                  EXISTS (SELECT 1 FROM prepared_work_order_demo_event
                          WHERE work_order_id = %s AND operation = 'finish'),
                  (SELECT count(*) FROM prepared_field_measurement WHERE work_order_id = %s),
                  (SELECT count(DISTINCT planned_point_id) FROM prepared_field_measurement
                   WHERE work_order_id = %s),
                  (SELECT count(DISTINCT manifest.planned_point_id)
                   FROM prepared_field_photo_manifest manifest
                   JOIN prepared_photo_upload_receipt receipt
                     ON receipt.photo_id = manifest.photo_id
                   JOIN prepared_photo_human_review review ON review.photo_id = receipt.photo_id
                   WHERE manifest.work_order_id = %s AND review.decision = 'accepted'
                     AND review.quality_status = 'accepted' AND review.ruler_status = 'visible'
                     AND NOT EXISTS (SELECT 1 FROM prepared_photo_human_review newer
                                     WHERE newer.supersedes_review_id = review.id))
                """,
            (work_order_id, work_order_id, work_order_id, work_order_id),
        )
        evidence = await cursor.fetchone()
        if evidence != (True, 3, 3, 3):
            raise SummaryEvidenceIncompleteError
        await cursor.execute(
            """
                INSERT INTO prepared_inspection_summary (
                    work_order_id, generated_by_user_id, summary_policy_id,
                    idempotency_key, generation_rationale, measurement_count,
                    accepted_photo_review_count, minimum_height_cm, maximum_height_cm,
                    mean_height_cm, n1_count, n2_count, n3_count, location_status,
                    evidence_status, data_status, eligible_for_field_evidence,
                    eligible_for_model_training, eligible_for_official_reporting,
                    authorizes_field_work)
                SELECT %s, %s, %s, %s, %s, 3, 3, min(height_cm), max(height_cm),
                       avg(height_cm)::numeric(9,4),
                       count(*) FILTER (WHERE height_cm < 10),
                       count(*) FILTER (WHERE height_cm >= 10 AND height_cm <= 30),
                       count(*) FILTER (WHERE height_cm > 30),
                       'simulated', 'prepared_reviewed_non_operational', 'prepared',
                       false, false, false, false
                FROM prepared_field_measurement WHERE work_order_id = %s
                ON CONFLICT (idempotency_key) DO NOTHING RETURNING id
                """,
            (
                work_order_id,
                actor.id,
                policy[0],
                key_hash,
                request.generation_rationale,
                work_order_id,
            ),
        )
        inserted = await cursor.fetchone()
        if not inserted:
            existing = await self._by_key(cursor, key_hash)
            if not existing:
                raise SummaryAlreadyExistsError
            if (existing[1], existing[2], existing[3]) != (
                work_order_id,
                actor.id,
                request.generation_rationale,
            ):
                raise SummaryIdempotencyConflictError
            return await self._response(cursor, existing[0])
        return await self._response(cursor, inserted[0])

    async def _by_key(self, cursor, key_hash: str):
        await cursor.execute(
            "SELECT id, work_order_id, generated_by_user_id, generation_rationale "
            "FROM prepared_inspection_summary WHERE idempotency_key = %s",
            (key_hash,),
        )
        return await cursor.fetchone()

    async def _response(self, cursor, summary_id: UUID) -> PreparedSummaryResponse:
        await cursor.execute(
            """SELECT summary.id, summary.work_order_id, policy.version,
                      summary.generation_rationale, summary.measurement_count,
                      summary.accepted_photo_review_count, summary.minimum_height_cm,
                      summary.maximum_height_cm, summary.mean_height_cm, summary.n1_count,
                      summary.n2_count, summary.n3_count, summary.generated_at
               FROM prepared_inspection_summary summary
               JOIN prepared_inspection_summary_policy policy
                 ON policy.id = summary.summary_policy_id
               WHERE summary.id = %s""",
            (summary_id,),
        )
        row = await cursor.fetchone()
        return self._response_from_row(row)

    @staticmethod
    def _response_from_row(row: tuple) -> PreparedSummaryResponse:
        return PreparedSummaryResponse(
            summary_id=row[0],
            work_order_id=row[1],
            summary_policy_version=row[2],
            generation_rationale=row[3],
            measurement_count=row[4],
            accepted_photo_review_count=row[5],
            minimum_height_cm=row[6],
            maximum_height_cm=row[7],
            mean_height_cm=row[8],
            n1_count=row[9],
            n2_count=row[10],
            n3_count=row[11],
            generated_at=row[12],
        )


async def get_prepared_summary_writer() -> PreparedSummaryWriter:
    settings = get_settings()
    return PostgresPreparedSummaryRepository(
        settings.database_url, settings.prepared_inspection_summary_policy_version
    )


async def get_prepared_summary_reader() -> PreparedSummaryReader:
    settings = get_settings()
    return PostgresPreparedSummaryRepository(
        settings.database_url, settings.prepared_inspection_summary_policy_version
    )


router = APIRouter(prefix="/v1/work-orders", tags=["work-orders"])
collection_router = APIRouter(
    prefix="/v1/prepared-inspection-summaries", tags=["work-orders"]
)


@collection_router.get("", response_model=PreparedSummaryCollection)
async def list_prepared_summaries(
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reader: Annotated[PreparedSummaryReader, Depends(get_prepared_summary_reader)],
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> PreparedSummaryCollection:
    return await reader.list_for_actor(actor=actor, limit=limit)


@router.post("/{work_order_id}/prepared-summary", response_model=PreparedSummaryResponse)
async def create_prepared_summary(
    work_order_id: UUID,
    request: PreparedSummaryRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[PreparedSummaryWriter, Depends(get_prepared_summary_writer)],
) -> PreparedSummaryResponse:
    try:
        return await writer.create(
            work_order_id=work_order_id,
            actor=actor,
            idempotency_key=idempotency_key,
            request=request,
        )
    except SummaryTargetNotFoundError:
        raise HTTPException(404, "Prepared order not found") from None
    except SummaryPermissionError:
        raise HTTPException(403, "User cannot summarize this road") from None
    except SummaryPolicyUnavailableError:
        raise HTTPException(503, "Summary policy unavailable") from None
    except SummaryEvidenceIncompleteError:
        raise HTTPException(409, "Prepared evidence is incomplete") from None
    except SummaryIdempotencyConflictError:
        raise HTTPException(409, "Idempotency-Key conflict") from None
    except SummaryAlreadyExistsError:
        raise HTTPException(409, "Prepared summary already exists") from None
