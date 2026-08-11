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

PlanningDecision = Literal["approved_for_planning", "changes_requested", "rejected"]


class PreparedMowingPlanningApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    readiness_assessment_id: UUID
    decision: PlanningDecision
    decision_rationale: str = Field(min_length=1, max_length=2000)
    supersedes_approval_id: UUID | None = None

    @field_validator("decision_rationale")
    @classmethod
    def normalize_rationale(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("planning approval rationale cannot be blank")
        return normalized


class PreparedMowingPlanningApprovalResponse(BaseModel):
    planning_approval_id: UUID
    mowing_order_id: UUID
    readiness_assessment_id: UUID
    decision: PlanningDecision
    decision_rationale: str
    supersedes_approval_id: UUID | None
    policy_version: str
    approval_effect: Literal["planning_only_no_execution_authorization"]
    dual_approval_requirement_status: Literal["pending_official_policy_validation"]
    operational_approval_satisfied: Literal[False]
    data_status: Literal["prepared"]
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    decided_at: datetime


class PlanningApprovalOrderNotFoundError(Exception):
    pass


class PlanningApprovalSourceError(Exception):
    pass


class PlanningApprovalDecisionError(Exception):
    pass


class PlanningApprovalPermissionError(Exception):
    pass


class PlanningApprovalPolicyUnavailableError(Exception):
    pass


class PlanningApprovalSupersessionError(Exception):
    pass


class PlanningApprovalIdempotencyConflictError(Exception):
    pass


class PreparedMowingPlanningApprovalWriter(Protocol):
    async def create(
        self, *, mowing_order_id: UUID, actor: AuthenticatedUser,
        idempotency_key: str, request: PreparedMowingPlanningApprovalRequest,
    ) -> PreparedMowingPlanningApprovalResponse: ...


class PostgresPreparedMowingPlanningApprovalRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self, *, mowing_order_id: UUID, actor: AuthenticatedUser,
        idempotency_key: str, request: PreparedMowingPlanningApprovalRequest,
    ) -> PreparedMowingPlanningApprovalResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT proposal_id FROM prepared_mowing_order WHERE id = %s",
                (mowing_order_id,),
            )
            source = await cursor.fetchone()
            if source is None:
                raise PlanningApprovalOrderNotFoundError
            for lock_key in (
                f"prepared-post-inspection-review:{source[0]}",
                f"prepared-mowing-resource-plan:{mowing_order_id}",
                f"prepared-mowing-readiness:{mowing_order_id}",
                f"prepared-mowing-planning-approval:{request.readiness_assessment_id}",
            ):
                await cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,)
                )
            target = await self._load_target(
                cursor, mowing_order_id, request.readiness_assessment_id
            )
            if target is None:
                raise PlanningApprovalSourceError
            if request.decision == "approved_for_planning" and target[1:3] != (
                "clear", "clear"
            ):
                raise PlanningApprovalDecisionError
            await cursor.execute(
                """SELECT id, allowed_roles, version
                   FROM prepared_mowing_planning_approval_policy
                   WHERE version = %s AND data_status = 'prepared'
                     AND dual_approval_requirement_status = 'pending_official_policy_validation'
                     AND NOT satisfies_operational_approval AND NOT authorizes_field_work
                     AND NOT eligible_for_field_execution""",
                (self._policy_version,),
            )
            policy = await cursor.fetchone()
            if policy is None:
                raise PlanningApprovalPolicyUnavailableError
            await cursor.execute(
                """SELECT 1 FROM road_user_role assignment
                   WHERE assignment.user_id = %s AND assignment.road_id = %s
                     AND assignment.role = ANY(%s)
                     AND assignment.data_status <> 'simulated' LIMIT 1""",
                (actor.id, target[0], policy[1]),
            )
            if not await cursor.fetchone():
                raise PlanningApprovalPermissionError
            existing = await self._by_key(cursor, key_hash)
            if existing is not None:
                self._assert_replay(existing, mowing_order_id, actor, request)
                return self._response(existing)
            await cursor.execute(
                """SELECT approval.id FROM prepared_mowing_planning_approval approval
                   WHERE approval.readiness_assessment_id = %s
                     AND NOT EXISTS (
                         SELECT 1 FROM prepared_mowing_planning_approval newer
                         WHERE newer.supersedes_approval_id = approval.id)
                   ORDER BY approval.decided_at DESC LIMIT 1""",
                (request.readiness_assessment_id,),
            )
            effective = await cursor.fetchone()
            if (effective is None and request.supersedes_approval_id is not None) or (
                effective is not None and request.supersedes_approval_id != effective[0]
            ):
                raise PlanningApprovalSupersessionError
            await cursor.execute(
                """
                INSERT INTO prepared_mowing_planning_approval (
                    mowing_order_id, readiness_assessment_id, decided_by_user_id,
                    policy_id, supersedes_approval_id, idempotency_key, decision,
                    decision_rationale, approval_effect, dual_approval_requirement_status,
                    operational_approval_satisfied, data_status, authorizes_field_work,
                    eligible_for_field_execution, eligible_for_official_reporting)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                        'planning_only_no_execution_authorization',
                        'pending_official_policy_validation', false, 'prepared',
                        false, false, false)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id, mowing_order_id, readiness_assessment_id,
                          decided_by_user_id, decision, decision_rationale,
                          supersedes_approval_id, approval_effect,
                          dual_approval_requirement_status,
                          operational_approval_satisfied, data_status, decided_at
                """,
                (
                    mowing_order_id, request.readiness_assessment_id, actor.id,
                    policy[0], request.supersedes_approval_id, key_hash,
                    request.decision, request.decision_rationale,
                ),
            )
            inserted = await cursor.fetchone()
            if inserted is None:
                existing = await self._by_key(cursor, key_hash)
                if existing is None:
                    raise PlanningApprovalIdempotencyConflictError
                self._assert_replay(existing, mowing_order_id, actor, request)
                return self._response(existing)
            return self._response((*inserted, policy[2]))

    async def _load_target(self, cursor, mowing_order_id, assessment_id):
        await cursor.execute(
            """SELECT axis.road_id, assessment.weather_result, assessment.safety_result
               FROM prepared_mowing_order mowing
               JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
               JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
               JOIN road_segment segment ON segment.id = zone.road_segment_id
               JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
               JOIN prepared_mowing_resource_plan plan ON plan.mowing_order_id = mowing.id
               JOIN prepared_mowing_readiness_assessment assessment
                 ON assessment.resource_plan_id = plan.id
               WHERE mowing.id = %s AND assessment.id = %s
                 AND NOT EXISTS (
                     SELECT 1 FROM prepared_post_inspection_review correction
                     WHERE correction.supersedes_review_id = mowing.source_review_id)
                 AND NOT EXISTS (
                     SELECT 1 FROM prepared_mowing_resource_plan newer_plan
                     WHERE newer_plan.supersedes_plan_id = plan.id)
                 AND NOT EXISTS (
                     SELECT 1 FROM prepared_mowing_readiness_assessment newer_assessment
                     WHERE newer_assessment.supersedes_assessment_id = assessment.id)
                 AND assessment.validation_status = 'prepared_manual_pending_validation'
                 AND assessment.requires_operational_approval
                 AND NOT assessment.authorizes_field_work
                 AND NOT assessment.eligible_for_field_execution
                 AND NOT assessment.eligible_for_official_reporting""",
            (mowing_order_id, assessment_id),
        )
        return await cursor.fetchone()

    async def _by_key(self, cursor, key_hash):
        await cursor.execute(
            """SELECT approval.id, approval.mowing_order_id,
                      approval.readiness_assessment_id, approval.decided_by_user_id,
                      approval.decision, approval.decision_rationale,
                      approval.supersedes_approval_id, approval.approval_effect,
                      approval.dual_approval_requirement_status,
                      approval.operational_approval_satisfied, approval.data_status,
                      approval.decided_at, policy.version
               FROM prepared_mowing_planning_approval approval
               JOIN prepared_mowing_planning_approval_policy policy
                 ON policy.id = approval.policy_id
               WHERE approval.idempotency_key = %s""",
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_replay(row, mowing_order_id, actor, request):
        if row[1:7] != (
            mowing_order_id, request.readiness_assessment_id, actor.id,
            request.decision, request.decision_rationale, request.supersedes_approval_id,
        ):
            raise PlanningApprovalIdempotencyConflictError

    @staticmethod
    def _response(row):
        return PreparedMowingPlanningApprovalResponse(
            planning_approval_id=row[0], mowing_order_id=row[1],
            readiness_assessment_id=row[2], decision=row[4], decision_rationale=row[5],
            supersedes_approval_id=row[6], approval_effect=row[7],
            dual_approval_requirement_status=row[8], operational_approval_satisfied=row[9],
            data_status=row[10], decided_at=row[11], policy_version=row[12],
        )


async def get_prepared_mowing_planning_approval_repository():
    settings = get_settings()
    return PostgresPreparedMowingPlanningApprovalRepository(
        settings.database_url, settings.prepared_mowing_approval_policy_version
    )


router = APIRouter(prefix="/v1/prepared-mowing-orders", tags=["prepared-mowing-approvals"])


@router.post(
    "/{mowing_order_id}/planning-approvals",
    response_model=PreparedMowingPlanningApprovalResponse,
)
async def create_prepared_mowing_planning_approval(
    mowing_order_id: UUID,
    request: PreparedMowingPlanningApprovalRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[
        PreparedMowingPlanningApprovalWriter,
        Depends(get_prepared_mowing_planning_approval_repository),
    ],
) -> PreparedMowingPlanningApprovalResponse:
    try:
        return await writer.create(
            mowing_order_id=mowing_order_id, actor=actor,
            idempotency_key=idempotency_key, request=request,
        )
    except PlanningApprovalOrderNotFoundError:
        raise HTTPException(404, "Prepared mowing order not found") from None
    except PlanningApprovalSourceError:
        raise HTTPException(409, "Effective readiness assessment is required") from None
    except PlanningApprovalDecisionError:
        raise HTTPException(409, "Planning approval requires clear prepared assessments") from None
    except PlanningApprovalPermissionError:
        raise HTTPException(403, "Actor cannot approve planning for this road") from None
    except PlanningApprovalPolicyUnavailableError:
        raise HTTPException(503, "Prepared planning-approval policy is unavailable") from None
    except PlanningApprovalSupersessionError:
        raise HTTPException(409, "Approval must supersede the effective approval") from None
    except PlanningApprovalIdempotencyConflictError:
        raise HTTPException(409, "Idempotency-Key conflict") from None
