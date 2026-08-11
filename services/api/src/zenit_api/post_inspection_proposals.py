from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


class PreparedProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    creation_rationale: str = Field(min_length=1, max_length=2000)

    @field_validator("creation_rationale")
    @classmethod
    def normalize_rationale(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("creation rationale cannot be blank")
        return normalized


class PreparedProposalResponse(BaseModel):
    proposal_id: UUID
    summary_id: UUID
    work_order_id: UUID
    road_code: str
    segment_index: int
    zone_type: Literal["left", "right", "median", "special"]
    policy_version: str
    creation_rationale: str
    recommendation: Literal["monitor", "mowing_review"]
    applicable_threshold_cm: Decimal
    maximum_height_cm: Decimal
    threshold_exceeded: bool
    requires_human_review: Literal[True] = True
    location_status: Literal["simulated"] = "simulated"
    evidence_status: Literal["prepared_reviewed_non_operational"] = (
        "prepared_reviewed_non_operational"
    )
    data_status: Literal["prepared"] = "prepared"
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    created_at: datetime
    review_count: int = 0
    latest_review_id: UUID | None = None
    latest_review_decision: Literal["accepted", "rejected", "adjusted"] | None = None
    latest_adjusted_recommendation: Literal["monitor", "mowing_review"] | None = None
    latest_review_rationale: str | None = None
    latest_reviewed_at: datetime | None = None
    review_state: Literal["awaiting_review", "review_recorded_no_work_authorization"] = (
        "awaiting_review"
    )
    prepared_mowing_order_id: UUID | None = None
    mowing_order_state: Literal[
        "not_prepared", "prepared_no_execution_authorization"
    ] = "not_prepared"
    resource_plan_count: int = Field(default=0, ge=0)
    latest_resource_plan_id: UUID | None = None
    latest_team_reference: str | None = None
    latest_equipment_reference: str | None = None
    latest_resource_plan_rationale: str | None = None
    latest_resource_plan_created_at: datetime | None = None
    readiness_assessment_count: int = Field(default=0, ge=0)
    latest_readiness_assessment_id: UUID | None = None
    latest_readiness_resource_plan_id: UUID | None = None
    latest_weather_result: Literal["clear", "blocked", "inconclusive"] | None = None
    latest_weather_source_reference: str | None = None
    latest_safety_result: Literal["clear", "blocked", "inconclusive"] | None = None
    latest_safety_source_reference: str | None = None
    latest_readiness_rationale: str | None = None
    latest_readiness_assessed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_review_state(self) -> PreparedProposalResponse:
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
                raise ValueError("unreviewed proposal cannot expose review metadata")
        elif (
            self.latest_review_id is None
            or self.latest_review_decision is None
            or self.latest_reviewed_at is None
            or self.review_state != "review_recorded_no_work_authorization"
            or (self.latest_review_decision == "adjusted")
            != (self.latest_adjusted_recommendation is not None)
        ):
            raise ValueError("reviewed proposal requires one consistent effective review")
        effective_recommendation = (
            self.latest_adjusted_recommendation
            if self.latest_review_decision == "adjusted"
            else self.recommendation if self.latest_review_decision == "accepted" else None
        )
        if (self.prepared_mowing_order_id is not None) != (
            self.mowing_order_state == "prepared_no_execution_authorization"
        ) or (
            self.prepared_mowing_order_id is not None
            and effective_recommendation != "mowing_review"
        ):
            raise ValueError("prepared mowing order requires an effective mowing-review decision")
        resource_metadata = (
            self.latest_resource_plan_id, self.latest_team_reference,
            self.latest_equipment_reference, self.latest_resource_plan_rationale,
            self.latest_resource_plan_created_at,
        )
        if self.resource_plan_count == 0:
            if any(value is not None for value in resource_metadata):
                raise ValueError("unplanned mowing order cannot expose resource metadata")
        elif self.prepared_mowing_order_id is None or any(
            value is None for value in resource_metadata
        ):
            raise ValueError("resource plan requires a current prepared mowing order")
        readiness_metadata = (
            self.latest_readiness_assessment_id, self.latest_readiness_resource_plan_id,
            self.latest_weather_result, self.latest_weather_source_reference,
            self.latest_safety_result, self.latest_safety_source_reference,
            self.latest_readiness_rationale, self.latest_readiness_assessed_at,
        )
        if self.readiness_assessment_count == 0:
            if any(value is not None for value in readiness_metadata):
                raise ValueError("unassessed mowing order cannot expose readiness metadata")
        elif (
            any(value is None for value in readiness_metadata)
            or self.latest_readiness_resource_plan_id != self.latest_resource_plan_id
        ):
            raise ValueError("readiness assessment requires the effective resource plan")
        return self


class PreparedProposalReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["accepted", "rejected", "adjusted"]
    adjusted_recommendation: Literal["monitor", "mowing_review"] | None = None
    rationale: str | None = Field(default=None, max_length=2000)
    supersedes_review_id: UUID | None = None

    @field_validator("rationale")
    @classmethod
    def normalize_review_rationale(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_review(self) -> PreparedProposalReviewRequest:
        if (self.decision == "adjusted") != (self.adjusted_recommendation is not None):
            raise ValueError("adjusted decision requires exactly one replacement")
        if self.decision in {"rejected", "adjusted"} and self.rationale is None:
            raise ValueError("rejected and adjusted decisions require a rationale")
        return self


class PreparedProposalReviewResponse(BaseModel):
    review_id: UUID
    proposal_id: UUID
    decision: Literal["accepted", "rejected", "adjusted"]
    adjusted_recommendation: Literal["monitor", "mowing_review"] | None
    rationale: str | None
    supersedes_review_id: UUID | None
    policy_version: str
    data_status: Literal["prepared"] = "prepared"
    eligible_for_official_reporting: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    reviewed_at: datetime


class PreparedProposalCollection(BaseModel):
    items: list[PreparedProposalResponse]
    result_count: int
    limit: int
    truncated: bool
    warning: str = (
        "Prepared proposals require a separate human decision and never authorize mowing."
    )


class ProposalNotFoundError(Exception):
    pass


class ProposalPermissionError(Exception):
    pass


class ProposalPolicyUnavailableError(Exception):
    pass


class ProposalIdempotencyConflictError(Exception):
    pass


class ProposalAlreadyExistsError(Exception):
    pass


class ProposalReviewSupersessionError(Exception):
    pass


class PreparedProposalWriter(Protocol):
    async def create(
        self,
        *,
        summary_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedProposalRequest,
    ) -> PreparedProposalResponse: ...


class PreparedProposalReader(Protocol):
    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> PreparedProposalCollection: ...


class PreparedProposalReviewWriter(Protocol):
    async def record_review(
        self,
        *,
        proposal_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedProposalReviewRequest,
    ) -> PreparedProposalReviewResponse: ...


class PostgresPreparedProposalRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self,
        *,
        summary_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedProposalRequest,
    ) -> PreparedProposalResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        try:
            async with connection, connection.cursor() as cursor:
                existing = await self._by_key(cursor, key_hash)
                if existing:
                    if existing[1:4] != (summary_id, actor.id, request.creation_rationale):
                        raise ProposalIdempotencyConflictError
                    return await self._response(cursor, existing[0])
                await cursor.execute(
                    "SELECT 1 FROM prepared_post_inspection_proposal WHERE summary_id = %s",
                    (summary_id,),
                )
                if await cursor.fetchone():
                    raise ProposalAlreadyExistsError
                return await self._insert(cursor, summary_id, actor, key_hash, request)
        except UniqueViolation as error:
            if error.diag.constraint_name == "prepared_post_inspection_proposal_summary_id_key":
                raise ProposalAlreadyExistsError from None
            raise

    async def _insert(self, cursor, summary_id, actor, key_hash, request):
        await cursor.execute(
            """
            SELECT summary.maximum_height_cm, zone.zone_type, axis.road_id
            FROM prepared_inspection_summary summary
            JOIN work_order order_record ON order_record.id = summary.work_order_id
            JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            WHERE summary.id = %s AND summary.location_status = 'simulated'
              AND summary.data_status = 'prepared'
              AND NOT summary.eligible_for_official_reporting
              AND NOT summary.authorizes_field_work
            """,
            (summary_id,),
        )
        target = await cursor.fetchone()
        if not target:
            raise ProposalNotFoundError
        await cursor.execute(
            """SELECT id, allowed_roles, general_threshold_cm, special_threshold_cm
               FROM prepared_post_inspection_policy
               WHERE version = %s AND data_status = 'prepared'
                 AND requires_human_review AND NOT authorizes_field_work""",
            (self._policy_version,),
        )
        policy = await cursor.fetchone()
        if not policy:
            raise ProposalPolicyUnavailableError
        await cursor.execute(
            """SELECT 1 FROM road_user_role WHERE user_id = %s AND road_id = %s
               AND role = ANY(%s) AND data_status <> 'simulated' LIMIT 1""",
            (actor.id, target[2], policy[1]),
        )
        if not await cursor.fetchone():
            raise ProposalPermissionError
        threshold = policy[3] if target[1] == "special" else policy[2]
        exceeded = target[0] > threshold
        recommendation = "mowing_review" if exceeded else "monitor"
        await cursor.execute(
            """
            INSERT INTO prepared_post_inspection_proposal (
                summary_id, created_by_user_id, policy_id, idempotency_key,
                creation_rationale, recommendation, applicable_threshold_cm,
                maximum_height_cm, threshold_exceeded, requires_human_review,
                location_status, evidence_status, data_status,
                eligible_for_model_training, eligible_for_official_reporting,
                authorizes_field_work)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true, 'simulated',
                    'prepared_reviewed_non_operational', 'prepared', false, false, false)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id
            """,
            (
                summary_id, actor.id, policy[0], key_hash, request.creation_rationale,
                recommendation, threshold, target[0], exceeded,
            ),
        )
        inserted = await cursor.fetchone()
        if inserted is None:
            existing = await self._by_key(cursor, key_hash)
            if existing is None:
                raise ProposalIdempotencyConflictError
            if existing[1:4] != (summary_id, actor.id, request.creation_rationale):
                raise ProposalIdempotencyConflictError
            return await self._response(cursor, existing[0])
        return await self._response(cursor, inserted[0])

    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> PreparedProposalCollection:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                self._response_query(
                    """EXISTS (SELECT 1 FROM road_user_role assignment
                        WHERE assignment.user_id = %s AND assignment.road_id = road.id
                          AND assignment.role IN ('manager', 'supervisor')
                          AND assignment.data_status <> 'simulated')
                        ORDER BY proposal.created_at DESC, proposal.id LIMIT %s"""
                ),
                (actor.id, limit + 1),
            )
            rows = await cursor.fetchall()
        truncated = len(rows) > limit
        visible = rows[:limit]
        return PreparedProposalCollection(
            items=[self._from_row(row) for row in visible],
            result_count=len(visible), limit=limit, truncated=truncated,
        )

    async def record_review(
        self,
        *,
        proposal_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedProposalReviewRequest,
    ) -> PreparedProposalReviewResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT proposal.policy_id, policy.version, axis.road_id, policy.allowed_roles
                FROM prepared_post_inspection_proposal proposal
                JOIN prepared_post_inspection_policy policy ON policy.id = proposal.policy_id
                JOIN prepared_inspection_summary summary ON summary.id = proposal.summary_id
                JOIN work_order order_record ON order_record.id = summary.work_order_id
                JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                WHERE proposal.id = %s AND proposal.requires_human_review
                  AND proposal.data_status = 'prepared'
                  AND NOT proposal.eligible_for_official_reporting
                  AND NOT proposal.authorizes_field_work
                  AND policy.data_status = 'prepared' AND policy.requires_human_review
                  AND NOT policy.authorizes_field_work
                """,
                (proposal_id,),
            )
            target = await cursor.fetchone()
            if target is None:
                raise ProposalNotFoundError
            await cursor.execute(
                """SELECT 1 FROM road_user_role WHERE user_id = %s AND road_id = %s
                   AND role = ANY(%s)
                   AND data_status <> 'simulated' LIMIT 1""",
                (actor.id, target[2], target[3]),
            )
            if not await cursor.fetchone():
                raise ProposalPermissionError
            existing = await self._review_by_key(cursor, key_hash)
            if existing is not None:
                self._assert_review_replay(existing, proposal_id, actor, request)
                return self._review_response(existing)
            await cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"prepared-post-inspection-review:{proposal_id}",),
            )
            await cursor.execute(
                """SELECT review.id FROM prepared_post_inspection_review review
                   WHERE review.proposal_id = %s
                     AND NOT EXISTS (SELECT 1 FROM prepared_post_inspection_review newer
                                     WHERE newer.supersedes_review_id = review.id)
                   ORDER BY review.reviewed_at DESC LIMIT 1""",
                (proposal_id,),
            )
            effective = await cursor.fetchone()
            if (effective is None and request.supersedes_review_id is not None) or (
                effective is not None and request.supersedes_review_id != effective[0]
            ):
                raise ProposalReviewSupersessionError
            await cursor.execute(
                """
                INSERT INTO prepared_post_inspection_review (
                    proposal_id, reviewer_user_id, policy_id, supersedes_review_id,
                    idempotency_key, decision, adjusted_recommendation, rationale,
                    data_status, eligible_for_official_reporting, authorizes_field_work)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'prepared', false, false)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id, proposal_id, reviewer_user_id, decision,
                          adjusted_recommendation, rationale, supersedes_review_id,
                          reviewed_at
                """,
                (
                    proposal_id, actor.id, target[0], request.supersedes_review_id,
                    key_hash, request.decision, request.adjusted_recommendation,
                    request.rationale,
                ),
            )
            inserted = await cursor.fetchone()
            if inserted is None:
                existing = await self._review_by_key(cursor, key_hash)
                if existing is None:
                    raise ProposalIdempotencyConflictError
                self._assert_review_replay(existing, proposal_id, actor, request)
                return self._review_response(existing)
            return self._review_response((*inserted, target[1]))

    async def _by_key(self, cursor, key_hash):
        await cursor.execute(
            """SELECT id, summary_id, created_by_user_id, creation_rationale
               FROM prepared_post_inspection_proposal WHERE idempotency_key = %s""",
            (key_hash,),
        )
        return await cursor.fetchone()

    async def _review_by_key(self, cursor, key_hash):
        await cursor.execute(
            """SELECT review.id, review.proposal_id, review.reviewer_user_id,
                      review.decision, review.adjusted_recommendation, review.rationale,
                      review.supersedes_review_id, review.reviewed_at, policy.version
               FROM prepared_post_inspection_review review
               JOIN prepared_post_inspection_policy policy ON policy.id = review.policy_id
               WHERE review.idempotency_key = %s""",
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_review_replay(row, proposal_id, actor, request):
        expected = (
            proposal_id, actor.id, request.decision, request.adjusted_recommendation,
            request.rationale, request.supersedes_review_id,
        )
        if row[1:7] != expected:
            raise ProposalIdempotencyConflictError

    @staticmethod
    def _review_response(row) -> PreparedProposalReviewResponse:
        return PreparedProposalReviewResponse(
            review_id=row[0], proposal_id=row[1], decision=row[3],
            adjusted_recommendation=row[4], rationale=row[5],
            supersedes_review_id=row[6], reviewed_at=row[7], policy_version=row[8],
        )

    async def _response(self, cursor, proposal_id):
        await cursor.execute(self._response_query("proposal.id = %s"), (proposal_id,))
        return self._from_row(await cursor.fetchone())

    @staticmethod
    def _response_query(where_clause: str) -> str:
        return f"""SELECT proposal.id, proposal.summary_id, summary.work_order_id,
                   road.code, segment.segment_index, zone.zone_type, policy.version,
                   proposal.creation_rationale, proposal.recommendation,
                   proposal.applicable_threshold_cm, proposal.maximum_height_cm,
                   proposal.threshold_exceeded, proposal.created_at,
                   COALESCE(review_total.review_count, 0), latest.id, latest.decision,
                   latest.adjusted_recommendation, latest.rationale, latest.reviewed_at,
                   mowing.id, COALESCE(plan_total.plan_count, 0), latest_plan.id,
                   latest_plan.team_reference, latest_plan.equipment_reference,
                   latest_plan.planning_rationale, latest_plan.created_at,
                   COALESCE(readiness_total.assessment_count, 0), latest_readiness.id,
                   latest_readiness.resource_plan_id, latest_readiness.weather_result,
                   latest_readiness.weather_source_reference, latest_readiness.safety_result,
                   latest_readiness.safety_source_reference,
                   latest_readiness.assessment_rationale, latest_readiness.assessed_at
            FROM prepared_post_inspection_proposal proposal
            JOIN prepared_post_inspection_policy policy ON policy.id = proposal.policy_id
            JOIN prepared_inspection_summary summary ON summary.id = proposal.summary_id
            JOIN work_order order_record ON order_record.id = summary.work_order_id
            JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            LEFT JOIN LATERAL (
                SELECT count(*) AS review_count
                FROM prepared_post_inspection_review review
                WHERE review.proposal_id = proposal.id
            ) review_total ON true
            LEFT JOIN LATERAL (
                SELECT review.id, review.decision, review.adjusted_recommendation,
                       review.rationale, review.reviewed_at
                FROM prepared_post_inspection_review review
                WHERE review.proposal_id = proposal.id
                  AND NOT EXISTS (
                      SELECT 1 FROM prepared_post_inspection_review newer
                      WHERE newer.supersedes_review_id = review.id)
                ORDER BY review.reviewed_at DESC LIMIT 1
            ) latest ON true
            LEFT JOIN prepared_mowing_order mowing ON mowing.source_review_id = latest.id
            LEFT JOIN LATERAL (
                SELECT count(*) AS plan_count
                FROM prepared_mowing_resource_plan plan
                WHERE plan.mowing_order_id = mowing.id
            ) plan_total ON true
            LEFT JOIN LATERAL (
                SELECT plan.id, plan.team_reference, plan.equipment_reference,
                       plan.planning_rationale, plan.created_at
                FROM prepared_mowing_resource_plan plan
                WHERE plan.mowing_order_id = mowing.id
                  AND NOT EXISTS (
                      SELECT 1 FROM prepared_mowing_resource_plan newer
                      WHERE newer.supersedes_plan_id = plan.id)
                ORDER BY plan.created_at DESC LIMIT 1
            ) latest_plan ON true
            LEFT JOIN LATERAL (
                SELECT count(*) AS assessment_count
                FROM prepared_mowing_readiness_assessment assessment
                WHERE assessment.resource_plan_id = latest_plan.id
            ) readiness_total ON true
            LEFT JOIN LATERAL (
                SELECT assessment.id, assessment.resource_plan_id,
                       assessment.weather_result, assessment.weather_source_reference,
                       assessment.safety_result, assessment.safety_source_reference,
                       assessment.assessment_rationale, assessment.assessed_at
                FROM prepared_mowing_readiness_assessment assessment
                WHERE assessment.resource_plan_id = latest_plan.id
                  AND NOT EXISTS (
                      SELECT 1 FROM prepared_mowing_readiness_assessment newer
                      WHERE newer.supersedes_assessment_id = assessment.id)
                ORDER BY assessment.assessed_at DESC LIMIT 1
            ) latest_readiness ON true
            WHERE proposal.location_status = 'simulated' AND proposal.data_status = 'prepared'
              AND NOT proposal.eligible_for_official_reporting
              AND NOT proposal.authorizes_field_work AND {where_clause}"""

    @staticmethod
    def _from_row(row: tuple) -> PreparedProposalResponse:
        return PreparedProposalResponse(
            proposal_id=row[0], summary_id=row[1], work_order_id=row[2], road_code=row[3],
            segment_index=row[4], zone_type=row[5], policy_version=row[6],
            creation_rationale=row[7], recommendation=row[8],
            applicable_threshold_cm=row[9], maximum_height_cm=row[10],
            threshold_exceeded=row[11], created_at=row[12], review_count=row[13],
            latest_review_id=row[14], latest_review_decision=row[15],
            latest_adjusted_recommendation=row[16], latest_review_rationale=row[17],
            latest_reviewed_at=row[18],
            review_state=(
                "review_recorded_no_work_authorization" if row[14] else "awaiting_review"
            ),
            prepared_mowing_order_id=row[19],
            mowing_order_state=(
                "prepared_no_execution_authorization" if row[19] else "not_prepared"
            ),
            resource_plan_count=row[20], latest_resource_plan_id=row[21],
            latest_team_reference=row[22], latest_equipment_reference=row[23],
            latest_resource_plan_rationale=row[24], latest_resource_plan_created_at=row[25],
            readiness_assessment_count=row[26], latest_readiness_assessment_id=row[27],
            latest_readiness_resource_plan_id=row[28], latest_weather_result=row[29],
            latest_weather_source_reference=row[30], latest_safety_result=row[31],
            latest_safety_source_reference=row[32], latest_readiness_rationale=row[33],
            latest_readiness_assessed_at=row[34],
        )


async def get_prepared_proposal_repository():
    settings = get_settings()
    return PostgresPreparedProposalRepository(
        settings.database_url, settings.prepared_post_inspection_policy_version
    )


summary_router = APIRouter(prefix="/v1/prepared-inspection-summaries", tags=["work-orders"])
collection_router = APIRouter(prefix="/v1/prepared-post-inspection-proposals", tags=["work-orders"])


@summary_router.post(
    "/{summary_id}/post-inspection-proposal", response_model=PreparedProposalResponse
)
async def create_prepared_proposal(
    summary_id: UUID,
    request: PreparedProposalRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[PreparedProposalWriter, Depends(get_prepared_proposal_repository)],
) -> PreparedProposalResponse:
    try:
        return await writer.create(
            summary_id=summary_id, actor=actor, idempotency_key=idempotency_key, request=request
        )
    except ProposalNotFoundError:
        raise HTTPException(404, "Prepared summary not found") from None
    except ProposalPermissionError:
        raise HTTPException(403, "User cannot create a proposal for this road") from None
    except ProposalPolicyUnavailableError:
        raise HTTPException(503, "Prepared proposal policy unavailable") from None
    except ProposalIdempotencyConflictError:
        raise HTTPException(409, "Idempotency-Key conflict") from None
    except ProposalAlreadyExistsError:
        raise HTTPException(409, "Prepared proposal already exists") from None


@collection_router.get("", response_model=PreparedProposalCollection)
async def list_prepared_proposals(
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reader: Annotated[PreparedProposalReader, Depends(get_prepared_proposal_repository)],
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> PreparedProposalCollection:
    return await reader.list_for_actor(actor=actor, limit=limit)


@collection_router.post(
    "/{proposal_id}/decisions", response_model=PreparedProposalReviewResponse
)
async def review_prepared_proposal(
    proposal_id: UUID,
    request: PreparedProposalReviewRequest,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[
        PreparedProposalReviewWriter, Depends(get_prepared_proposal_repository)
    ],
) -> PreparedProposalReviewResponse:
    try:
        return await writer.record_review(
            proposal_id=proposal_id,
            actor=actor,
            idempotency_key=idempotency_key,
            request=request,
        )
    except ProposalNotFoundError:
        raise HTTPException(404, "Prepared proposal not found") from None
    except ProposalPermissionError:
        raise HTTPException(403, "User cannot review this road") from None
    except ProposalIdempotencyConflictError:
        raise HTTPException(409, "Idempotency-Key conflict") from None
    except ProposalReviewSupersessionError:
        raise HTTPException(409, "Review must supersede the effective proposal review") from None
