from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings

AssessmentResult = Literal["clear", "blocked", "inconclusive"]


class PreparedMowingReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_plan_id: UUID
    weather_result: AssessmentResult
    weather_source_reference: str = Field(min_length=1, max_length=500)
    safety_result: AssessmentResult
    safety_source_reference: str = Field(min_length=1, max_length=500)
    assessment_rationale: str = Field(min_length=1, max_length=2000)
    supersedes_assessment_id: UUID | None = None

    @field_validator(
        "weather_source_reference", "safety_source_reference", "assessment_rationale"
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prepared readiness text cannot be blank")
        return normalized


class PreparedMowingReadinessResponse(BaseModel):
    readiness_assessment_id: UUID
    mowing_order_id: UUID
    resource_plan_id: UUID
    weather_result: AssessmentResult
    weather_source_reference: str
    safety_result: AssessmentResult
    safety_source_reference: str
    assessment_rationale: str
    supersedes_assessment_id: UUID | None
    policy_version: str
    validation_status: Literal["prepared_manual_pending_validation"]
    data_status: Literal["prepared"]
    requires_operational_approval: Literal[True]
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    assessed_at: datetime


class ReadinessOrderNotFoundError(Exception):
    pass


class ReadinessSourceError(Exception):
    pass


class ReadinessPermissionError(Exception):
    pass


class ReadinessPolicyUnavailableError(Exception):
    pass


class ReadinessSupersessionError(Exception):
    pass


class ReadinessIdempotencyConflictError(Exception):
    pass


class PreparedMowingReadinessWriter(Protocol):
    async def create(
        self, *, mowing_order_id: UUID, actor: AuthenticatedUser,
        idempotency_key: str, request: PreparedMowingReadinessRequest,
    ) -> PreparedMowingReadinessResponse: ...


class PostgresPreparedMowingReadinessRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self, *, mowing_order_id: UUID, actor: AuthenticatedUser,
        idempotency_key: str, request: PreparedMowingReadinessRequest,
    ) -> PreparedMowingReadinessResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT proposal_id FROM prepared_mowing_order WHERE id = %s",
                (mowing_order_id,),
            )
            source = await cursor.fetchone()
            if source is None:
                raise ReadinessOrderNotFoundError
            for lock_key in (
                f"prepared-post-inspection-review:{source[0]}",
                f"prepared-mowing-resource-plan:{mowing_order_id}",
                f"prepared-mowing-readiness:{mowing_order_id}",
            ):
                await cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,)
                )
            target = await self._load_target(cursor, mowing_order_id, request.resource_plan_id)
            if target is None:
                raise ReadinessSourceError
            await cursor.execute(
                """SELECT id, allowed_roles, version FROM prepared_mowing_readiness_policy
                   WHERE version = %s AND data_status = 'prepared'
                     AND NOT manual_assessments_are_operational
                     AND requires_operational_approval AND NOT authorizes_field_work
                     AND NOT eligible_for_field_execution""",
                (self._policy_version,),
            )
            policy = await cursor.fetchone()
            if policy is None:
                raise ReadinessPolicyUnavailableError
            await cursor.execute(
                """SELECT 1 FROM road_user_role assignment
                   WHERE assignment.user_id = %s AND assignment.road_id = %s
                     AND assignment.role = ANY(%s)
                     AND assignment.data_status <> 'simulated' LIMIT 1""",
                (actor.id, target[0], policy[1]),
            )
            if not await cursor.fetchone():
                raise ReadinessPermissionError
            existing = await self._by_key(cursor, key_hash)
            if existing is not None:
                self._assert_replay(existing, mowing_order_id, actor, request)
                return self._response(existing)
            await cursor.execute(
                """SELECT assessment.id FROM prepared_mowing_readiness_assessment assessment
                   WHERE assessment.resource_plan_id = %s
                     AND NOT EXISTS (
                         SELECT 1 FROM prepared_mowing_readiness_assessment newer
                         WHERE newer.supersedes_assessment_id = assessment.id)
                   ORDER BY assessment.assessed_at DESC LIMIT 1""",
                (request.resource_plan_id,),
            )
            effective = await cursor.fetchone()
            if (effective is None and request.supersedes_assessment_id is not None) or (
                effective is not None and request.supersedes_assessment_id != effective[0]
            ):
                raise ReadinessSupersessionError
            await cursor.execute(
                """
                INSERT INTO prepared_mowing_readiness_assessment (
                    mowing_order_id, resource_plan_id, assessed_by_user_id, policy_id,
                    supersedes_assessment_id, idempotency_key, weather_result,
                    weather_source_reference, safety_result, safety_source_reference,
                    assessment_rationale, validation_status, data_status,
                    requires_operational_approval, authorizes_field_work,
                    eligible_for_field_execution, eligible_for_official_reporting)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        'prepared_manual_pending_validation', 'prepared', true,
                        false, false, false)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id, mowing_order_id, resource_plan_id, assessed_by_user_id,
                          weather_result, weather_source_reference, safety_result,
                          safety_source_reference, assessment_rationale,
                          supersedes_assessment_id, validation_status, data_status,
                          requires_operational_approval, assessed_at
                """,
                (
                    mowing_order_id, request.resource_plan_id, actor.id, policy[0],
                    request.supersedes_assessment_id, key_hash, request.weather_result,
                    request.weather_source_reference, request.safety_result,
                    request.safety_source_reference, request.assessment_rationale,
                ),
            )
            inserted = await cursor.fetchone()
            if inserted is None:
                existing = await self._by_key(cursor, key_hash)
                if existing is None:
                    raise ReadinessIdempotencyConflictError
                self._assert_replay(existing, mowing_order_id, actor, request)
                return self._response(existing)
            return self._response((*inserted, policy[2]))

    async def _load_target(self, cursor, mowing_order_id: UUID, resource_plan_id: UUID):
        await cursor.execute(
            """SELECT axis.road_id
               FROM prepared_mowing_order mowing
               JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
               JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
               JOIN road_segment segment ON segment.id = zone.road_segment_id
               JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
               JOIN prepared_mowing_resource_plan plan ON plan.mowing_order_id = mowing.id
               WHERE mowing.id = %s AND plan.id = %s
                 AND mowing.status = 'prepared' AND mowing.data_status = 'prepared'
                 AND mowing.location_status = 'simulated'
                 AND mowing.requires_operational_approval
                 AND NOT mowing.authorizes_field_work
                 AND NOT mowing.eligible_for_field_execution
                 AND NOT mowing.eligible_for_official_reporting
                 AND NOT EXISTS (
                     SELECT 1 FROM prepared_post_inspection_review correction
                     WHERE correction.supersedes_review_id = mowing.source_review_id)
                 AND NOT EXISTS (
                     SELECT 1 FROM prepared_mowing_resource_plan newer
                     WHERE newer.supersedes_plan_id = plan.id)
                 AND plan.resource_reference_status = 'prepared_placeholder_pending_validation'
                 AND plan.data_status = 'prepared'
                 AND plan.team_assignment_status = 'unassigned'
                 AND plan.equipment_assignment_status = 'unassigned'
                 AND plan.requires_operational_approval
                 AND NOT plan.authorizes_field_work
                 AND NOT plan.eligible_for_field_execution
                 AND NOT plan.eligible_for_official_reporting""",
            (mowing_order_id, resource_plan_id),
        )
        return await cursor.fetchone()

    async def _by_key(self, cursor, key_hash: str):
        await cursor.execute(
            """SELECT assessment.id, assessment.mowing_order_id,
                      assessment.resource_plan_id, assessment.assessed_by_user_id,
                      assessment.weather_result, assessment.weather_source_reference,
                      assessment.safety_result, assessment.safety_source_reference,
                      assessment.assessment_rationale, assessment.supersedes_assessment_id,
                      assessment.validation_status, assessment.data_status,
                      assessment.requires_operational_approval, assessment.assessed_at,
                      policy.version
               FROM prepared_mowing_readiness_assessment assessment
               JOIN prepared_mowing_readiness_policy policy ON policy.id = assessment.policy_id
               WHERE assessment.idempotency_key = %s""",
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_replay(row, mowing_order_id, actor, request) -> None:
        if row[1:10] != (
            mowing_order_id, request.resource_plan_id, actor.id, request.weather_result,
            request.weather_source_reference, request.safety_result,
            request.safety_source_reference, request.assessment_rationale,
            request.supersedes_assessment_id,
        ):
            raise ReadinessIdempotencyConflictError

    @staticmethod
    def _response(row) -> PreparedMowingReadinessResponse:
        return PreparedMowingReadinessResponse(
            readiness_assessment_id=row[0], mowing_order_id=row[1], resource_plan_id=row[2],
            weather_result=row[4], weather_source_reference=row[5], safety_result=row[6],
            safety_source_reference=row[7], assessment_rationale=row[8],
            supersedes_assessment_id=row[9], validation_status=row[10], data_status=row[11],
            requires_operational_approval=row[12], assessed_at=row[13], policy_version=row[14],
        )


async def get_prepared_mowing_readiness_repository() -> (
    PostgresPreparedMowingReadinessRepository
):
    settings = get_settings()
    return PostgresPreparedMowingReadinessRepository(
        settings.database_url, settings.prepared_mowing_readiness_policy_version
    )


router = APIRouter(prefix="/v1/prepared-mowing-orders", tags=["prepared-mowing-readiness"])


@router.post(
    "/{mowing_order_id}/readiness-assessments",
    response_model=PreparedMowingReadinessResponse,
)
async def create_prepared_mowing_readiness_assessment(
    mowing_order_id: UUID,
    request: PreparedMowingReadinessRequest,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[
        PreparedMowingReadinessWriter, Depends(get_prepared_mowing_readiness_repository)
    ],
) -> PreparedMowingReadinessResponse:
    try:
        return await writer.create(
            mowing_order_id=mowing_order_id, actor=actor,
            idempotency_key=idempotency_key, request=request,
        )
    except ReadinessOrderNotFoundError:
        raise HTTPException(404, "Prepared mowing order not found") from None
    except ReadinessSourceError:
        raise HTTPException(409, "Current order and resource plan are required") from None
    except ReadinessPermissionError:
        raise HTTPException(403, "Actor cannot assess readiness for this road") from None
    except ReadinessPolicyUnavailableError:
        raise HTTPException(503, "Prepared mowing-readiness policy is unavailable") from None
    except ReadinessSupersessionError:
        raise HTTPException(409, "Assessment must supersede the effective assessment") from None
    except ReadinessIdempotencyConflictError:
        raise HTTPException(409, "Idempotency-Key conflict") from None
