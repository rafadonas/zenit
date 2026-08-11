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


class PreparedMowingResourcePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_reference: str = Field(min_length=1, max_length=200)
    equipment_reference: str = Field(min_length=1, max_length=200)
    planning_rationale: str = Field(min_length=1, max_length=2000)
    supersedes_plan_id: UUID | None = None

    @field_validator("team_reference", "equipment_reference", "planning_rationale")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prepared resource-plan text cannot be blank")
        return normalized


class PreparedMowingResourcePlanResponse(BaseModel):
    resource_plan_id: UUID
    mowing_order_id: UUID
    team_reference: str
    equipment_reference: str
    planning_rationale: str
    supersedes_plan_id: UUID | None
    policy_version: str
    resource_reference_status: Literal["prepared_placeholder_pending_validation"]
    data_status: Literal["prepared"]
    team_assignment_status: Literal["unassigned"]
    equipment_assignment_status: Literal["unassigned"]
    requires_operational_approval: Literal[True]
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    created_at: datetime


class ResourcePlanOrderNotFoundError(Exception):
    pass


class ResourcePlanOrderObsoleteError(Exception):
    pass


class ResourcePlanPermissionError(Exception):
    pass


class ResourcePlanPolicyUnavailableError(Exception):
    pass


class ResourcePlanSupersessionError(Exception):
    pass


class ResourcePlanIdempotencyConflictError(Exception):
    pass


class PreparedMowingResourcePlanWriter(Protocol):
    async def create(
        self,
        *,
        mowing_order_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedMowingResourcePlanRequest,
    ) -> PreparedMowingResourcePlanResponse: ...


class PostgresPreparedMowingResourcePlanRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self,
        *,
        mowing_order_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedMowingResourcePlanRequest,
    ) -> PreparedMowingResourcePlanResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT proposal_id FROM prepared_mowing_order WHERE id = %s",
                (mowing_order_id,),
            )
            source = await cursor.fetchone()
            if source is None:
                raise ResourcePlanOrderNotFoundError
            await cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"prepared-post-inspection-review:{source[0]}",),
            )
            target = await self._load_target(cursor, mowing_order_id)
            if target is None:
                raise ResourcePlanOrderNotFoundError
            if target[1] is not None:
                raise ResourcePlanOrderObsoleteError
            await cursor.execute(
                """SELECT id, allowed_roles, version FROM prepared_mowing_resource_plan_policy
                   WHERE version = %s AND data_status = 'prepared'
                     AND NOT resource_references_are_verified
                     AND requires_operational_approval AND NOT authorizes_field_work
                     AND NOT eligible_for_field_execution""",
                (self._policy_version,),
            )
            policy = await cursor.fetchone()
            if policy is None:
                raise ResourcePlanPolicyUnavailableError
            await cursor.execute(
                """SELECT 1 FROM road_user_role assignment
                   WHERE assignment.user_id = %s AND assignment.road_id = %s
                     AND assignment.role = ANY(%s)
                     AND assignment.data_status <> 'simulated' LIMIT 1""",
                (actor.id, target[0], policy[1]),
            )
            if not await cursor.fetchone():
                raise ResourcePlanPermissionError
            existing = await self._by_key(cursor, key_hash)
            if existing is not None:
                self._assert_replay(existing, mowing_order_id, actor, request)
                return self._response(existing)
            await cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"prepared-mowing-resource-plan:{mowing_order_id}",),
            )
            await cursor.execute(
                """SELECT plan.id FROM prepared_mowing_resource_plan plan
                   WHERE plan.mowing_order_id = %s
                     AND NOT EXISTS (
                         SELECT 1 FROM prepared_mowing_resource_plan newer
                         WHERE newer.supersedes_plan_id = plan.id)
                   ORDER BY plan.created_at DESC LIMIT 1""",
                (mowing_order_id,),
            )
            effective = await cursor.fetchone()
            if (effective is None and request.supersedes_plan_id is not None) or (
                effective is not None and request.supersedes_plan_id != effective[0]
            ):
                raise ResourcePlanSupersessionError
            await cursor.execute(
                """
                INSERT INTO prepared_mowing_resource_plan (
                    mowing_order_id, created_by_user_id, policy_id, supersedes_plan_id,
                    idempotency_key, team_reference, equipment_reference,
                    planning_rationale, resource_reference_status, data_status,
                    team_assignment_status, equipment_assignment_status,
                    requires_operational_approval, authorizes_field_work,
                    eligible_for_field_execution, eligible_for_official_reporting)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                        'prepared_placeholder_pending_validation', 'prepared',
                        'unassigned', 'unassigned', true, false, false, false)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id, mowing_order_id, created_by_user_id, team_reference,
                          equipment_reference, planning_rationale, supersedes_plan_id,
                          resource_reference_status, data_status, team_assignment_status,
                          equipment_assignment_status, requires_operational_approval, created_at
                """,
                (
                    mowing_order_id, actor.id, policy[0], request.supersedes_plan_id,
                    key_hash, request.team_reference, request.equipment_reference,
                    request.planning_rationale,
                ),
            )
            inserted = await cursor.fetchone()
            if inserted is None:
                existing = await self._by_key(cursor, key_hash)
                if existing is None:
                    raise ResourcePlanIdempotencyConflictError
                self._assert_replay(existing, mowing_order_id, actor, request)
                return self._response(existing)
            return self._response((*inserted, policy[2]))

    async def _load_target(self, cursor, mowing_order_id: UUID):
        await cursor.execute(
            """SELECT axis.road_id, correction.id
               FROM prepared_mowing_order mowing
               JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
               JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
               JOIN road_segment segment ON segment.id = zone.road_segment_id
               JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
               LEFT JOIN prepared_post_inspection_review correction
                 ON correction.supersedes_review_id = mowing.source_review_id
               WHERE mowing.id = %s AND mowing.status = 'prepared'
                 AND mowing.data_status = 'prepared' AND mowing.location_status = 'simulated'
                 AND mowing.team_assignment_status = 'unassigned'
                 AND mowing.equipment_assignment_status = 'unassigned'
                 AND mowing.weather_check_status = 'pending'
                 AND mowing.safety_check_status = 'pending'
                 AND mowing.requires_operational_approval
                 AND NOT mowing.authorizes_field_work
                 AND NOT mowing.eligible_for_field_execution
                 AND NOT mowing.eligible_for_official_reporting""",
            (mowing_order_id,),
        )
        return await cursor.fetchone()

    async def _by_key(self, cursor, key_hash: str):
        await cursor.execute(
            """SELECT plan.id, plan.mowing_order_id, plan.created_by_user_id,
                      plan.team_reference, plan.equipment_reference,
                      plan.planning_rationale, plan.supersedes_plan_id,
                      plan.resource_reference_status, plan.data_status,
                      plan.team_assignment_status, plan.equipment_assignment_status,
                      plan.requires_operational_approval, plan.created_at, policy.version
               FROM prepared_mowing_resource_plan plan
               JOIN prepared_mowing_resource_plan_policy policy ON policy.id = plan.policy_id
               WHERE plan.idempotency_key = %s""",
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_replay(row, mowing_order_id, actor, request) -> None:
        if row[1:7] != (
            mowing_order_id, actor.id, request.team_reference,
            request.equipment_reference, request.planning_rationale,
            request.supersedes_plan_id,
        ):
            raise ResourcePlanIdempotencyConflictError

    @staticmethod
    def _response(row) -> PreparedMowingResourcePlanResponse:
        return PreparedMowingResourcePlanResponse(
            resource_plan_id=row[0], mowing_order_id=row[1], team_reference=row[3],
            equipment_reference=row[4], planning_rationale=row[5],
            supersedes_plan_id=row[6], resource_reference_status=row[7],
            data_status=row[8], team_assignment_status=row[9],
            equipment_assignment_status=row[10], requires_operational_approval=row[11],
            created_at=row[12], policy_version=row[13],
        )


async def get_prepared_mowing_resource_plan_repository() -> (
    PostgresPreparedMowingResourcePlanRepository
):
    settings = get_settings()
    return PostgresPreparedMowingResourcePlanRepository(
        settings.database_url, settings.prepared_mowing_resource_policy_version
    )


router = APIRouter(
    prefix="/v1/prepared-mowing-orders", tags=["prepared-mowing-resource-plans"]
)


@router.post(
    "/{mowing_order_id}/resource-plans",
    response_model=PreparedMowingResourcePlanResponse,
)
async def create_prepared_mowing_resource_plan(
    mowing_order_id: UUID,
    request: PreparedMowingResourcePlanRequest,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[
        PreparedMowingResourcePlanWriter,
        Depends(get_prepared_mowing_resource_plan_repository),
    ],
) -> PreparedMowingResourcePlanResponse:
    try:
        return await writer.create(
            mowing_order_id=mowing_order_id, actor=actor,
            idempotency_key=idempotency_key, request=request,
        )
    except ResourcePlanOrderNotFoundError:
        raise HTTPException(404, "Prepared mowing order not found") from None
    except ResourcePlanOrderObsoleteError:
        raise HTTPException(409, "Mowing order source review is no longer effective") from None
    except ResourcePlanPermissionError:
        raise HTTPException(403, "Creator cannot plan resources for this road") from None
    except ResourcePlanPolicyUnavailableError:
        raise HTTPException(503, "Prepared mowing-resource policy is unavailable") from None
    except ResourcePlanSupersessionError:
        raise HTTPException(409, "Resource plan must supersede the effective plan") from None
    except ResourcePlanIdempotencyConflictError:
        raise HTTPException(409, "Idempotency-Key conflict") from None
