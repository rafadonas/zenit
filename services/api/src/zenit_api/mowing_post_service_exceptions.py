from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


class MowingPostServiceExceptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    creation_rationale: str = Field(min_length=1, max_length=2000)

    @field_validator("creation_rationale")
    @classmethod
    def normalize(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("creation rationale cannot be blank")
        return value


class MowingPostServiceExceptionResponse(BaseModel):
    exception_id: UUID
    summary_id: UUID
    mowing_order_id: UUID
    road_code: str
    segment_index: int
    zone_type: Literal["left", "right", "median", "special"]
    policy_version: str
    creation_rationale: str
    recommendation: Literal["monitor", "inspect_follow_up"]
    applicable_threshold_cm: Decimal
    maximum_height_cm: Decimal
    threshold_exceeded: bool
    requires_human_review: Literal[True] = True
    phase: Literal["post_service"] = "post_service"
    data_status: Literal["simulated"] = "simulated"
    location_status: Literal["not_collected"] = "not_collected"
    evidence_status: Literal["simulated_reviewed_non_operational"] = (
        "simulated_reviewed_non_operational"
    )
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    created_at: datetime
    review_count: int = Field(default=0, ge=0)
    latest_review_id: UUID | None = None
    latest_review_decision: Literal["accepted", "rejected", "adjusted"] | None = None
    latest_adjusted_recommendation: Literal["monitor", "inspect_follow_up"] | None = None
    latest_review_rationale: str | None = None
    latest_reviewed_at: datetime | None = None
    review_state: Literal["awaiting_review", "review_recorded_no_work_authorization"] = (
        "awaiting_review"
    )

    @model_validator(mode="after")
    def validate_review_state(self) -> MowingPostServiceExceptionResponse:
        if self.review_count == 0:
            if any(
                value is not None
                for value in (
                    self.latest_review_id,
                    self.latest_review_decision,
                    self.latest_adjusted_recommendation,
                    self.latest_review_rationale,
                    self.latest_reviewed_at,
                )
            ) or self.review_state != "awaiting_review":
                raise ValueError("unreviewed exception cannot expose review metadata")
        elif (
            self.latest_review_id is None
            or self.latest_review_decision is None
            or self.latest_reviewed_at is None
            or self.review_state != "review_recorded_no_work_authorization"
            or (self.latest_review_decision == "adjusted")
            != (self.latest_adjusted_recommendation is not None)
        ):
            raise ValueError("reviewed exception requires one consistent effective review")
        return self


class MowingPostServiceExceptionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["accepted", "rejected", "adjusted"]
    adjusted_recommendation: Literal["monitor", "inspect_follow_up"] | None = None
    rationale: str | None = Field(default=None, max_length=2000)
    supersedes_review_id: UUID | None = None

    @field_validator("rationale")
    @classmethod
    def normalize_rationale(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_review(self) -> MowingPostServiceExceptionReviewRequest:
        if (self.decision == "adjusted") != (self.adjusted_recommendation is not None):
            raise ValueError("adjusted decision requires exactly one replacement")
        if self.decision in {"rejected", "adjusted"} and self.rationale is None:
            raise ValueError("rejected and adjusted decisions require a rationale")
        return self


class MowingPostServiceExceptionReviewResponse(BaseModel):
    review_id: UUID
    exception_id: UUID
    decision: Literal["accepted", "rejected", "adjusted"]
    adjusted_recommendation: Literal["monitor", "inspect_follow_up"] | None
    rationale: str | None
    supersedes_review_id: UUID | None
    policy_version: str
    phase: Literal["post_service"] = "post_service"
    data_status: Literal["simulated"] = "simulated"
    eligible_for_official_reporting: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    reviewed_at: datetime


class MowingPostServiceExceptionCollection(BaseModel):
    items: list[MowingPostServiceExceptionResponse]
    result_count: int
    limit: int
    truncated: bool
    warning: str = (
        "Simulated post-service exceptions only request human follow-up review; "
        "they never authorize field work or official reporting."
    )


class ExceptionNotFound(Exception):
    pass


class ExceptionForbidden(Exception):
    pass


class ExceptionPolicyUnavailable(Exception):
    pass


class ExceptionAlreadyExists(Exception):
    pass


class ExceptionIdempotencyConflict(Exception):
    pass


class ExceptionReviewSupersession(Exception):
    pass


class MowingPostServiceExceptionRepository(Protocol):
    async def create(
        self,
        *,
        summary_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: MowingPostServiceExceptionRequest,
    ) -> MowingPostServiceExceptionResponse: ...

    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> MowingPostServiceExceptionCollection: ...

    async def record_review(
        self,
        *,
        exception_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: MowingPostServiceExceptionReviewRequest,
    ) -> MowingPostServiceExceptionReviewResponse: ...


class PostgresMowingPostServiceExceptionRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self,
        *,
        summary_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: MowingPostServiceExceptionRequest,
    ) -> MowingPostServiceExceptionResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            existing = await self._by_key(cursor, key_hash)
            if existing is not None:
                if existing[1:] != (summary_id, actor.id, request.creation_rationale):
                    raise ExceptionIdempotencyConflict
                return await self._response(cursor, existing[0])
            await cursor.execute(
                "SELECT 1 FROM prepared_mowing_post_service_exception WHERE summary_id=%s",
                (summary_id,),
            )
            if await cursor.fetchone():
                raise ExceptionAlreadyExists
            await cursor.execute(
                """
                SELECT summary.mowing_order_id, summary.maximum_height_cm, zone.zone_type,
                       axis.road_id
                FROM prepared_mowing_post_service_summary summary
                JOIN prepared_mowing_order mowing ON mowing.id = summary.mowing_order_id
                JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
                JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                WHERE summary.id=%s AND summary.phase='post_service'
                  AND summary.data_status='simulated'
                  AND summary.location_status='not_collected'
                  AND NOT summary.eligible_for_official_reporting
                  AND NOT summary.authorizes_field_work
                """,
                (summary_id,),
            )
            target = await cursor.fetchone()
            if target is None:
                raise ExceptionNotFound
            await cursor.execute(
                """
                SELECT id, allowed_roles, general_threshold_cm, special_threshold_cm
                FROM prepared_mowing_post_service_exception_policy
                WHERE version=%s AND data_status='prepared'
                  AND requires_human_review AND NOT authorizes_field_work
                """,
                (self._policy_version,),
            )
            policy = await cursor.fetchone()
            if policy is None:
                raise ExceptionPolicyUnavailable
            await cursor.execute(
                """SELECT 1 FROM road_user_role WHERE user_id=%s AND road_id=%s
                   AND role=ANY(%s) AND data_status <> 'simulated' LIMIT 1""",
                (actor.id, target[3], policy[1]),
            )
            if not await cursor.fetchone():
                raise ExceptionForbidden
            threshold = policy[3] if target[2] == "special" else policy[2]
            exceeded = target[1] > threshold
            recommendation = "inspect_follow_up" if exceeded else "monitor"
            await cursor.execute(
                """
                INSERT INTO prepared_mowing_post_service_exception (
                    summary_id, created_by_user_id, policy_id, idempotency_key,
                    creation_rationale, recommendation, applicable_threshold_cm,
                    maximum_height_cm, threshold_exceeded, requires_human_review,
                    phase, data_status, location_status, evidence_status,
                    eligible_for_model_training, eligible_for_official_reporting,
                    authorizes_field_work)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,true,'post_service','simulated',
                        'not_collected','simulated_reviewed_non_operational',false,false,false)
                RETURNING id
                """,
                (
                    summary_id, actor.id, policy[0], key_hash, request.creation_rationale,
                    recommendation, threshold, target[1], exceeded,
                ),
            )
            inserted = await cursor.fetchone()
            return await self._response(cursor, inserted[0])

    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> MowingPostServiceExceptionCollection:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                self._query(
                    """EXISTS (SELECT 1 FROM road_user_role assignment
                       WHERE assignment.user_id=%s AND assignment.road_id=axis.road_id
                         AND assignment.role IN ('manager','supervisor')
                         AND assignment.data_status <> 'simulated')
                       ORDER BY exception.created_at DESC, exception.id LIMIT %s"""
                ),
                (actor.id, limit + 1),
            )
            rows = await cursor.fetchall()
        items = [self._row(row) for row in rows[:limit]]
        return MowingPostServiceExceptionCollection(
            items=items, result_count=len(items), limit=limit, truncated=len(rows) > limit
        )

    async def record_review(
        self,
        *,
        exception_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: MowingPostServiceExceptionReviewRequest,
    ) -> MowingPostServiceExceptionReviewResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT exception.policy_id, policy.version, axis.road_id, policy.allowed_roles
                FROM prepared_mowing_post_service_exception exception
                JOIN prepared_mowing_post_service_exception_policy policy
                  ON policy.id = exception.policy_id
                JOIN prepared_mowing_post_service_summary summary
                  ON summary.id = exception.summary_id
                JOIN prepared_mowing_order mowing ON mowing.id = summary.mowing_order_id
                JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
                JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                WHERE exception.id=%s AND exception.requires_human_review
                  AND exception.phase='post_service'
                  AND exception.data_status='simulated'
                  AND NOT exception.eligible_for_official_reporting
                  AND NOT exception.authorizes_field_work
                  AND policy.data_status='prepared'
                  AND policy.requires_human_review
                  AND NOT policy.authorizes_field_work
                """,
                (exception_id,),
            )
            target = await cursor.fetchone()
            if target is None:
                raise ExceptionNotFound
            await cursor.execute(
                """SELECT 1 FROM road_user_role WHERE user_id=%s AND road_id=%s
                   AND role=ANY(%s) AND data_status <> 'simulated' LIMIT 1""",
                (actor.id, target[2], target[3]),
            )
            if not await cursor.fetchone():
                raise ExceptionForbidden
            existing = await self._review_by_key(cursor, key_hash)
            if existing is not None:
                self._assert_review_replay(existing, exception_id, actor, request)
                return self._review_response(existing)
            await cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"mowing-post-service-exception-review:{exception_id}",),
            )
            await cursor.execute(
                """
                SELECT review.id FROM prepared_mowing_post_service_exception_review review
                WHERE review.exception_id=%s
                  AND NOT EXISTS (
                      SELECT 1 FROM prepared_mowing_post_service_exception_review newer
                      WHERE newer.supersedes_review_id = review.id)
                ORDER BY review.reviewed_at DESC LIMIT 1
                """,
                (exception_id,),
            )
            effective = await cursor.fetchone()
            if (effective is None and request.supersedes_review_id is not None) or (
                effective is not None and request.supersedes_review_id != effective[0]
            ):
                raise ExceptionReviewSupersession
            await cursor.execute(
                """
                INSERT INTO prepared_mowing_post_service_exception_review (
                    exception_id, reviewer_user_id, policy_id, supersedes_review_id,
                    idempotency_key, decision, adjusted_recommendation, rationale,
                    phase, data_status, eligible_for_official_reporting, authorizes_field_work)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'post_service','simulated',false,false)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id, exception_id, reviewer_user_id, decision,
                          adjusted_recommendation, rationale, supersedes_review_id,
                          reviewed_at
                """,
                (
                    exception_id, actor.id, target[0], request.supersedes_review_id,
                    key_hash, request.decision, request.adjusted_recommendation,
                    request.rationale,
                ),
            )
            inserted = await cursor.fetchone()
            if inserted is None:
                existing = await self._review_by_key(cursor, key_hash)
                if existing is None:
                    raise ExceptionIdempotencyConflict
                self._assert_review_replay(existing, exception_id, actor, request)
                return self._review_response(existing)
            return self._review_response((*inserted, target[1]))

    async def _by_key(self, cursor, key_hash):
        await cursor.execute(
            """
            SELECT id, summary_id, created_by_user_id, creation_rationale
            FROM prepared_mowing_post_service_exception
            WHERE idempotency_key=%s
            """,
            (key_hash,),
        )
        return await cursor.fetchone()

    async def _review_by_key(self, cursor, key_hash):
        await cursor.execute(
            """
            SELECT review.id, review.exception_id, review.reviewer_user_id,
                   review.decision, review.adjusted_recommendation, review.rationale,
                   review.supersedes_review_id, review.reviewed_at, policy.version
            FROM prepared_mowing_post_service_exception_review review
            JOIN prepared_mowing_post_service_exception_policy policy
              ON policy.id = review.policy_id
            WHERE review.idempotency_key=%s
            """,
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_review_replay(row, exception_id, actor, request):
        expected = (
            exception_id, actor.id, request.decision, request.adjusted_recommendation,
            request.rationale, request.supersedes_review_id,
        )
        if row[1:7] != expected:
            raise ExceptionIdempotencyConflict

    @staticmethod
    def _review_response(row) -> MowingPostServiceExceptionReviewResponse:
        return MowingPostServiceExceptionReviewResponse(
            review_id=row[0],
            exception_id=row[1],
            decision=row[3],
            adjusted_recommendation=row[4],
            rationale=row[5],
            supersedes_review_id=row[6],
            reviewed_at=row[7],
            policy_version=row[8],
        )

    async def _response(self, cursor, exception_id):
        await cursor.execute(self._query("exception.id=%s"), (exception_id,))
        return self._row(await cursor.fetchone())

    @staticmethod
    def _query(where_clause: str) -> str:
        return f"""
            SELECT exception.id, exception.summary_id, summary.mowing_order_id,
                   road.code, segment.segment_index, zone.zone_type, policy.version,
                   exception.creation_rationale, exception.recommendation,
                   exception.applicable_threshold_cm, exception.maximum_height_cm,
                   exception.threshold_exceeded, exception.created_at,
                   COALESCE(review_total.review_count, 0), latest.id, latest.decision,
                   latest.adjusted_recommendation, latest.rationale, latest.reviewed_at
            FROM prepared_mowing_post_service_exception exception
            JOIN prepared_mowing_post_service_summary summary ON summary.id = exception.summary_id
            JOIN prepared_mowing_order mowing ON mowing.id = summary.mowing_order_id
            JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
            JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            JOIN prepared_mowing_post_service_exception_policy policy
              ON policy.id = exception.policy_id
            LEFT JOIN LATERAL (
                SELECT count(*) AS review_count
                FROM prepared_mowing_post_service_exception_review review
                WHERE review.exception_id = exception.id
            ) review_total ON true
            LEFT JOIN LATERAL (
                SELECT review.id, review.decision, review.adjusted_recommendation,
                       review.rationale, review.reviewed_at
                FROM prepared_mowing_post_service_exception_review review
                WHERE review.exception_id = exception.id
                  AND NOT EXISTS (
                      SELECT 1 FROM prepared_mowing_post_service_exception_review newer
                      WHERE newer.supersedes_review_id = review.id)
                ORDER BY review.reviewed_at DESC LIMIT 1
            ) latest ON true
            WHERE {where_clause}
              AND exception.phase = 'post_service'
              AND exception.data_status = 'simulated'
              AND exception.location_status = 'not_collected'
              AND NOT exception.eligible_for_official_reporting
              AND NOT exception.authorizes_field_work
            """

    @staticmethod
    def _row(row) -> MowingPostServiceExceptionResponse:
        return MowingPostServiceExceptionResponse(
            exception_id=row[0],
            summary_id=row[1],
            mowing_order_id=row[2],
            road_code=row[3],
            segment_index=row[4],
            zone_type=row[5],
            policy_version=row[6],
            creation_rationale=row[7],
            recommendation=row[8],
            applicable_threshold_cm=row[9],
            maximum_height_cm=row[10],
            threshold_exceeded=row[11],
            created_at=row[12],
            review_count=row[13],
            latest_review_id=row[14],
            latest_review_decision=row[15],
            latest_adjusted_recommendation=row[16],
            latest_review_rationale=row[17],
            latest_reviewed_at=row[18],
            review_state=(
                "review_recorded_no_work_authorization" if row[14] else "awaiting_review"
            ),
        )


async def get_exception_repository():
    settings = get_settings()
    return PostgresMowingPostServiceExceptionRepository(
        settings.database_url,
        settings.prepared_mowing_post_service_exception_policy_version,
    )


router = APIRouter(
    prefix="/v1/prepared-mowing-post-service-summaries",
    tags=["prepared-mowing-orders"],
)
collection_router = APIRouter(
    prefix="/v1/prepared-mowing-post-service-exceptions",
    tags=["prepared-mowing-orders"],
)


@router.post("/{summary_id}/exceptions", response_model=MowingPostServiceExceptionResponse)
async def create_exception(
    summary_id: UUID,
    request: MowingPostServiceExceptionRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[
        MowingPostServiceExceptionRepository, Depends(get_exception_repository)
    ],
):
    try:
        return await repository.create(
            summary_id=summary_id,
            actor=actor,
            idempotency_key=idempotency_key,
            request=request,
        )
    except ExceptionNotFound:
        raise HTTPException(404, "Simulated mowing post-service summary not found") from None
    except ExceptionForbidden:
        raise HTTPException(403, "User lacks a role for this road") from None
    except ExceptionPolicyUnavailable:
        raise HTTPException(503, "Post-service exception policy is unavailable") from None
    except (ExceptionAlreadyExists, ExceptionIdempotencyConflict):
        raise HTTPException(409, "Post-service exception already exists or key conflicts") from None


@collection_router.get("", response_model=MowingPostServiceExceptionCollection)
async def list_exceptions(
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[
        MowingPostServiceExceptionRepository, Depends(get_exception_repository)
    ],
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
):
    return await repository.list_for_actor(actor=actor, limit=limit)


@collection_router.post(
    "/{exception_id}/decisions",
    response_model=MowingPostServiceExceptionReviewResponse,
)
async def review_exception(
    exception_id: UUID,
    request: MowingPostServiceExceptionReviewRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[
        MowingPostServiceExceptionRepository, Depends(get_exception_repository)
    ],
):
    try:
        return await repository.record_review(
            exception_id=exception_id,
            actor=actor,
            idempotency_key=idempotency_key,
            request=request,
        )
    except ExceptionNotFound:
        raise HTTPException(404, "Simulated mowing post-service exception not found") from None
    except ExceptionForbidden:
        raise HTTPException(403, "User cannot review this road") from None
    except ExceptionIdempotencyConflict:
        raise HTTPException(409, "Idempotency-Key conflict") from None
    except ExceptionReviewSupersession:
        raise HTTPException(409, "Review must supersede the effective exception review") from None
