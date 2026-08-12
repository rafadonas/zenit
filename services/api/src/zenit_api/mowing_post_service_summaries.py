from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


class MowingPostServiceSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generation_rationale: str = Field(min_length=1, max_length=2000)

    @field_validator("generation_rationale")
    @classmethod
    def normalize(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("generation rationale cannot be blank")
        return value


class MowingPostServiceSummaryResponse(BaseModel):
    summary_id: UUID
    mowing_order_id: UUID
    summary_policy_version: str
    generation_rationale: str
    measurement_count: Literal[3] = 3
    accepted_photo_review_count: Literal[3] = 3
    minimum_height_cm: Decimal
    maximum_height_cm: Decimal
    mean_height_cm: Decimal
    n1_count: int
    n2_count: int
    n3_count: int
    phase: str = "post_service"
    summary_scope: str = "mowing_demo_post_service_only"
    location_status: str = "not_collected"
    data_status: str = "simulated"
    evidence_status: str = "simulated_reviewed_non_operational"
    eligible_for_field_evidence: bool = False
    eligible_for_field_execution: bool = False
    eligible_for_model_training: bool = False
    eligible_for_official_reporting: bool = False
    authorizes_field_work: bool = False
    generated_at: datetime


class MowingPostServiceSummaryCollection(BaseModel):
    items: list[MowingPostServiceSummaryResponse]
    result_count: int
    limit: int
    truncated: bool
    warning: str = (
        "Resumo pós-serviço simulado; não comprova roçada, eficácia, conclusão ou operação oficial."
    )


class SummaryError(Exception):
    pass


class SummaryNotFound(SummaryError):
    pass


class SummaryForbidden(SummaryError):
    pass


class SummaryPolicyUnavailable(SummaryError):
    pass


class SummaryEvidenceIncomplete(SummaryError):
    pass


class SummaryIdempotencyConflict(SummaryError):
    pass


class SummaryAlreadyExists(SummaryError):
    pass


class MowingSummaryWriter(Protocol):
    async def create(
        self,
        *,
        mowing_order_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: MowingPostServiceSummaryRequest,
    ) -> MowingPostServiceSummaryResponse: ...


class MowingSummaryReader(Protocol):
    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> MowingPostServiceSummaryCollection: ...


class PostgresMowingSummaryRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self,
        *,
        mowing_order_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: MowingPostServiceSummaryRequest,
    ) -> MowingPostServiceSummaryResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"prepared-mowing-summary:{mowing_order_id}",),
            )
            existing = await self._by_key(cursor, key_hash)
            if existing:
                if existing[1:] != (mowing_order_id, actor.id, request.generation_rationale):
                    raise SummaryIdempotencyConflict
                return await self._response(cursor, existing[0])
            await cursor.execute(
                "SELECT id, version, allowed_roles FROM prepared_mowing_post_service_summary_policy WHERE version=%s AND data_status='prepared' AND NOT authorizes_field_work",  # noqa: E501
                (self._policy_version,),
            )
            policy = await cursor.fetchone()
            if not policy:
                raise SummaryPolicyUnavailable
            await cursor.execute(
                """SELECT axis.road_id FROM prepared_mowing_order mowing JOIN work_order inspection ON inspection.id=mowing.source_inspection_work_order_id JOIN segment_zone zone ON zone.id=inspection.segment_zone_id JOIN road_segment segment ON segment.id=zone.road_segment_id JOIN road_axis_candidate axis ON axis.id=segment.road_axis_candidate_id WHERE mowing.id=%s AND mowing.status='prepared' AND mowing.data_status='prepared' AND mowing.location_status='simulated' AND NOT mowing.authorizes_field_work""",  # noqa: E501
                (mowing_order_id,),
            )
            target = await cursor.fetchone()
            if not target:
                raise SummaryNotFound
            await cursor.execute(
                "SELECT 1 FROM road_user_role WHERE user_id=%s AND road_id=%s AND role=ANY(%s) AND data_status<>'simulated'",  # noqa: E501
                (actor.id, target[0], policy[2]),
            )
            if not await cursor.fetchone():
                raise SummaryForbidden
            await cursor.execute(
                """SELECT count(*)::integer, min(height_cm), max(height_cm), avg(height_cm)::numeric(9,4), count(*) FILTER (WHERE height_cm < 10)::integer, count(*) FILTER (WHERE height_cm >= 10 AND height_cm <= 30)::integer, count(*) FILTER (WHERE height_cm > 30)::integer FROM prepared_mowing_post_service_measurement WHERE mowing_order_id=%s""",  # noqa: E501
                (mowing_order_id,),
            )
            aggregates = await cursor.fetchone()
            await cursor.execute(
                """SELECT count(*)::integer FROM prepared_mowing_post_service_photo_manifest manifest JOIN prepared_mowing_post_service_photo_upload_receipt receipt ON receipt.photo_id=manifest.photo_id JOIN prepared_mowing_post_service_photo_human_review review ON review.photo_id=manifest.photo_id WHERE manifest.mowing_order_id=%s AND receipt.content_status='uploaded_unverified' AND review.decision='accepted' AND review.quality_status='accepted' AND review.ruler_status='visible' AND NOT EXISTS (SELECT 1 FROM prepared_mowing_post_service_photo_human_review newer WHERE newer.supersedes_review_id=review.id)""",  # noqa: E501
                (mowing_order_id,),
            )
            accepted = (await cursor.fetchone())[0]
            if aggregates[0] != 3 or accepted != 3:
                raise SummaryEvidenceIncomplete
            await cursor.execute(
                """INSERT INTO prepared_mowing_post_service_summary (mowing_order_id, generated_by_user_id, summary_policy_id, idempotency_key, generation_rationale, measurement_count, accepted_photo_review_count, minimum_height_cm, maximum_height_cm, mean_height_cm, n1_count, n2_count, n3_count, phase, summary_scope, location_status, data_status, evidence_status, eligible_for_field_evidence, eligible_for_field_execution, eligible_for_model_training, eligible_for_official_reporting, authorizes_field_work) VALUES (%s,%s,%s,%s,%s,3,3,%s,%s,%s,%s,%s,%s,'post_service','mowing_demo_post_service_only','not_collected','simulated','simulated_reviewed_non_operational',false,false,false,false,false) RETURNING id""",  # noqa: E501
                (
                    mowing_order_id,
                    actor.id,
                    policy[0],
                    key_hash,
                    request.generation_rationale,
                    *aggregates[1:],
                ),
            )
            inserted = await cursor.fetchone()
            if not inserted:
                raise SummaryAlreadyExists
            return await self._response(cursor, inserted[0])

    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> MowingPostServiceSummaryCollection:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """SELECT summary.id, summary.mowing_order_id, policy.version, summary.generation_rationale, summary.measurement_count, summary.accepted_photo_review_count, summary.minimum_height_cm, summary.maximum_height_cm, summary.mean_height_cm, summary.n1_count, summary.n2_count, summary.n3_count, summary.generated_at FROM prepared_mowing_post_service_summary summary JOIN prepared_mowing_post_service_summary_policy policy ON policy.id=summary.summary_policy_id JOIN prepared_mowing_order mowing ON mowing.id=summary.mowing_order_id JOIN work_order inspection ON inspection.id=mowing.source_inspection_work_order_id JOIN segment_zone zone ON zone.id=inspection.segment_zone_id JOIN road_segment segment ON segment.id=zone.road_segment_id JOIN road_axis_candidate axis ON axis.id=segment.road_axis_candidate_id WHERE EXISTS (SELECT 1 FROM road_user_role assignment WHERE assignment.user_id=%s AND assignment.road_id=axis.road_id AND assignment.role IN ('manager','supervisor') AND assignment.data_status<>'simulated') ORDER BY summary.generated_at DESC, summary.id LIMIT %s""",  # noqa: E501
                (actor.id, limit + 1),
            )
            rows = await cursor.fetchall()
            items = [self._row(row) for row in rows[:limit]]
        return MowingPostServiceSummaryCollection(
            items=items, result_count=len(items), limit=limit, truncated=len(rows) > limit
        )

    async def _by_key(self, cursor, key_hash):
        await cursor.execute(
            "SELECT id, mowing_order_id, generated_by_user_id, generation_rationale FROM prepared_mowing_post_service_summary WHERE idempotency_key=%s",  # noqa: E501
            (key_hash,),
        )
        return await cursor.fetchone()

    async def _response(self, cursor, summary_id):
        await cursor.execute(
            "SELECT summary.id, summary.mowing_order_id, policy.version, summary.generation_rationale, summary.measurement_count, summary.accepted_photo_review_count, summary.minimum_height_cm, summary.maximum_height_cm, summary.mean_height_cm, summary.n1_count, summary.n2_count, summary.n3_count, summary.generated_at FROM prepared_mowing_post_service_summary summary JOIN prepared_mowing_post_service_summary_policy policy ON policy.id=summary.summary_policy_id WHERE summary.id=%s",  # noqa: E501
            (summary_id,),
        )
        return self._row(await cursor.fetchone())

    @staticmethod
    def _row(row):
        return MowingPostServiceSummaryResponse(
            summary_id=row[0],
            mowing_order_id=row[1],
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


async def get_mowing_summary_writer():
    settings = get_settings()
    return PostgresMowingSummaryRepository(
        settings.database_url, settings.prepared_mowing_post_service_summary_policy_version
    )


async def get_mowing_summary_reader():
    settings = get_settings()
    return PostgresMowingSummaryRepository(
        settings.database_url, settings.prepared_mowing_post_service_summary_policy_version
    )


router = APIRouter(prefix="/v1/prepared-mowing-orders", tags=["prepared-mowing-orders"])
summary_router = APIRouter(
    prefix="/v1/prepared-mowing-post-service-summaries", tags=["prepared-mowing-orders"]
)


@router.post(
    "/{mowing_order_id}/post-service-summary", response_model=MowingPostServiceSummaryResponse
)
async def create_summary(
    mowing_order_id: UUID,
    request: MowingPostServiceSummaryRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[MowingSummaryWriter, Depends(get_mowing_summary_writer)],
):
    try:
        return await writer.create(
            mowing_order_id=mowing_order_id,
            actor=actor,
            idempotency_key=idempotency_key,
            request=request,
        )
    except SummaryNotFound:
        raise HTTPException(404, "Prepared mowing order not found") from None
    except SummaryForbidden:
        raise HTTPException(403, "Reviewer lacks a role for this road") from None
    except SummaryPolicyUnavailable:
        raise HTTPException(503, "Post-service summary policy is unavailable") from None
    except SummaryEvidenceIncomplete:
        raise HTTPException(
            409, "Post-service summary requires three measurements and accepted photo reviews"
        ) from None
    except SummaryIdempotencyConflict:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Idempotency-Key was already used for another summary"
        ) from None


@summary_router.get("", response_model=MowingPostServiceSummaryCollection)
async def list_summaries(
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reader: Annotated[MowingSummaryReader, Depends(get_mowing_summary_reader)],
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
):
    return await reader.list_for_actor(actor=actor, limit=limit)
