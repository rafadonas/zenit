from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


class PreparedMowingOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_review_id: UUID
    planning_rationale: str = Field(min_length=1, max_length=2000)

    @field_validator("planning_rationale")
    @classmethod
    def normalize_rationale(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("planning rationale cannot be blank")
        return normalized


class PreparedMowingOrderResponse(BaseModel):
    mowing_order_id: UUID
    proposal_id: UUID
    source_review_id: UUID
    source_inspection_work_order_id: UUID
    road_code: str
    segment_index: int = Field(ge=0)
    zone_type: Literal["left", "right", "median", "special"]
    creation_recommendation: Literal["mowing_review"]
    source_review_state: Literal["effective", "superseded"]
    order_type: Literal["mowing"]
    status: Literal["prepared"]
    version: Literal[1]
    planning_rationale: str
    creation_policy_version: str
    data_status: Literal["prepared"]
    location_status: Literal["simulated"]
    source_evidence_status: Literal["prepared_reviewed_non_operational"]
    team_assignment_status: Literal["unassigned"]
    equipment_assignment_status: Literal["unassigned"]
    weather_check_status: Literal["pending"]
    safety_check_status: Literal["pending"]
    requires_operational_approval: Literal[True]
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    created_at: datetime
    resource_plan_count: int = Field(default=0, ge=0)
    latest_resource_plan_id: UUID | None = None
    latest_team_reference: str | None = None
    latest_equipment_reference: str | None = None
    latest_resource_plan_rationale: str | None = None
    latest_resource_plan_created_at: datetime | None = None
    resource_plan_state: Literal[
        "not_planned", "candidate_resources_pending_validation"
    ] = "not_planned"

    @model_validator(mode="after")
    def validate_resource_plan_state(self) -> PreparedMowingOrderResponse:
        metadata = (
            self.latest_resource_plan_id, self.latest_team_reference,
            self.latest_equipment_reference, self.latest_resource_plan_rationale,
            self.latest_resource_plan_created_at,
        )
        if self.resource_plan_count == 0:
            if (
                any(value is not None for value in metadata)
                or self.resource_plan_state != "not_planned"
            ):
                raise ValueError("unplanned mowing order cannot expose resource metadata")
        elif (
            any(value is None for value in metadata)
            or self.resource_plan_state != "candidate_resources_pending_validation"
        ):
            raise ValueError("planned mowing order requires one effective candidate resource plan")
        return self


class PreparedMowingOrderCollection(BaseModel):
    items: list[PreparedMowingOrderResponse]
    result_count: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    truncated: bool
    warning: str = (
        "Prepared mowing orders have no team, equipment, weather or safety clearance "
        "and never authorize field execution."
    )


class MowingOrderSourceNotFoundError(Exception):
    pass


class MowingOrderSourceDecisionError(Exception):
    pass


class MowingOrderPermissionError(Exception):
    pass


class MowingOrderPolicyUnavailableError(Exception):
    pass


class MowingOrderIdempotencyConflictError(Exception):
    pass


class MowingOrderAlreadyExistsError(Exception):
    pass


class PreparedMowingOrderRepository(Protocol):
    async def create(
        self,
        *,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedMowingOrderRequest,
    ) -> PreparedMowingOrderResponse: ...

    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> PreparedMowingOrderCollection: ...


class PostgresPreparedMowingOrderRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self,
        *,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedMowingOrderRequest,
    ) -> PreparedMowingOrderResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        try:
            async with connection, connection.cursor() as cursor:
                existing = await self._by_key(cursor, key_hash)
                if existing is not None:
                    self._assert_replay(existing, actor, request)
                    return await self._response(cursor, existing[0])

                await cursor.execute(
                    """
                    SELECT review.proposal_id
                    FROM prepared_post_inspection_review review
                    WHERE review.id = %s
                    """,
                    (request.source_review_id,),
                )
                source = await cursor.fetchone()
                if source is None:
                    raise MowingOrderSourceNotFoundError
                await cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (f"prepared-post-inspection-review:{source[0]}",),
                )
                target = await self._load_target(cursor, request.source_review_id)
                if target is None:
                    raise MowingOrderSourceNotFoundError
                if target[7] is not None or target[8] != "mowing_review":
                    raise MowingOrderSourceDecisionError

                await cursor.execute(
                    """SELECT id, allowed_roles FROM prepared_mowing_order_policy
                       WHERE version = %s AND data_status = 'prepared'
                         AND requires_team_assignment AND requires_operational_approval
                         AND NOT authorizes_field_work AND NOT eligible_for_field_execution""",
                    (self._policy_version,),
                )
                policy = await cursor.fetchone()
                if policy is None:
                    raise MowingOrderPolicyUnavailableError
                await cursor.execute(
                    """SELECT 1 FROM road_user_role assignment
                       WHERE assignment.user_id = %s AND assignment.road_id = %s
                         AND assignment.role = ANY(%s)
                         AND assignment.data_status <> 'simulated' LIMIT 1""",
                    (actor.id, target[6], policy[1]),
                )
                if not await cursor.fetchone():
                    raise MowingOrderPermissionError

                await cursor.execute(
                    """
                    INSERT INTO prepared_mowing_order (
                        proposal_id, source_review_id, source_inspection_work_order_id,
                        creation_policy_id, created_by_user_id, idempotency_key,
                        order_type, status, version, planning_rationale, data_status,
                        location_status, source_evidence_status, team_assignment_status,
                        equipment_assignment_status, weather_check_status, safety_check_status,
                        requires_operational_approval, authorizes_field_work,
                        eligible_for_field_execution, eligible_for_official_reporting)
                    VALUES (%s, %s, %s, %s, %s, %s, 'mowing', 'prepared', 1, %s,
                            'prepared', 'simulated', 'prepared_reviewed_non_operational',
                            'unassigned', 'unassigned', 'pending', 'pending', true,
                            false, false, false)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING id
                    """,
                    (
                        target[1], request.source_review_id, target[2], policy[0], actor.id,
                        key_hash, request.planning_rationale,
                    ),
                )
                inserted = await cursor.fetchone()
                if inserted is None:
                    existing = await self._by_key(cursor, key_hash)
                    if existing is None:
                        raise MowingOrderIdempotencyConflictError
                    self._assert_replay(existing, actor, request)
                    return await self._response(cursor, existing[0])
                return await self._response(cursor, inserted[0])
        except UniqueViolation as error:
            if error.diag.constraint_name == "prepared_mowing_order_source_review_id_key":
                raise MowingOrderAlreadyExistsError from None
            raise

    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> PreparedMowingOrderCollection:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT mowing.id
                FROM prepared_mowing_order mowing
                JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
                JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                WHERE EXISTS (
                    SELECT 1 FROM road_user_role assignment
                    WHERE assignment.user_id = %s AND assignment.road_id = axis.road_id
                      AND assignment.role IN ('manager', 'supervisor')
                      AND assignment.data_status <> 'simulated')
                ORDER BY mowing.created_at DESC, mowing.id LIMIT %s
                """,
                (actor.id, limit + 1),
            )
            ids = [row[0] for row in await cursor.fetchall()]
            truncated = len(ids) > limit
            items = [await self._response(cursor, order_id) for order_id in ids[:limit]]
        return PreparedMowingOrderCollection(
            items=items, result_count=len(items), limit=limit, truncated=truncated
        )

    async def _load_target(self, cursor, source_review_id: UUID):
        await cursor.execute(
            """
            SELECT review.id, proposal.id, summary.work_order_id, road.code,
                   segment.segment_index, zone.zone_type, axis.road_id, correction.id,
                   CASE WHEN review.decision = 'accepted' THEN proposal.recommendation
                        WHEN review.decision = 'adjusted' THEN review.adjusted_recommendation
                        ELSE NULL END
            FROM prepared_post_inspection_review review
            JOIN prepared_post_inspection_proposal proposal ON proposal.id = review.proposal_id
            JOIN prepared_inspection_summary summary ON summary.id = proposal.summary_id
            JOIN work_order inspection ON inspection.id = summary.work_order_id
            JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            LEFT JOIN prepared_post_inspection_review correction
              ON correction.supersedes_review_id = review.id
            WHERE review.id = %s AND review.policy_id = proposal.policy_id
              AND review.data_status = 'prepared'
              AND NOT review.eligible_for_official_reporting
              AND NOT review.authorizes_field_work
              AND proposal.data_status = 'prepared' AND proposal.location_status = 'simulated'
              AND proposal.evidence_status = 'prepared_reviewed_non_operational'
              AND NOT proposal.eligible_for_official_reporting
              AND NOT proposal.authorizes_field_work
            """,
            (source_review_id,),
        )
        return await cursor.fetchone()

    async def _by_key(self, cursor, key_hash: str):
        await cursor.execute(
            """SELECT id, source_review_id, created_by_user_id, planning_rationale
               FROM prepared_mowing_order WHERE idempotency_key = %s""",
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_replay(row, actor, request) -> None:
        if row[1:4] != (request.source_review_id, actor.id, request.planning_rationale):
            raise MowingOrderIdempotencyConflictError

    async def _response(self, cursor, mowing_order_id: UUID) -> PreparedMowingOrderResponse:
        await cursor.execute(
            """
            SELECT mowing.id, proposal.id, review.id, inspection.id, road.code,
                   segment.segment_index, zone.zone_type, 'mowing_review',
                   CASE WHEN EXISTS (
                       SELECT 1 FROM prepared_post_inspection_review correction
                       WHERE correction.supersedes_review_id = review.id
                   ) THEN 'superseded' ELSE 'effective' END,
                   mowing.order_type, mowing.status, mowing.version,
                   mowing.planning_rationale, policy.version, mowing.data_status,
                   mowing.location_status, mowing.source_evidence_status,
                   mowing.team_assignment_status, mowing.equipment_assignment_status,
                   mowing.weather_check_status, mowing.safety_check_status,
                   mowing.requires_operational_approval, mowing.created_at,
                   COALESCE(plan_total.plan_count, 0), latest_plan.id,
                   latest_plan.team_reference, latest_plan.equipment_reference,
                   latest_plan.planning_rationale, latest_plan.created_at
            FROM prepared_mowing_order mowing
            JOIN prepared_mowing_order_policy policy ON policy.id = mowing.creation_policy_id
            JOIN prepared_post_inspection_review review ON review.id = mowing.source_review_id
            JOIN prepared_post_inspection_proposal proposal ON proposal.id = mowing.proposal_id
            JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
            JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
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
            WHERE mowing.id = %s
            """,
            (mowing_order_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise MowingOrderSourceNotFoundError
        return PreparedMowingOrderResponse(
            mowing_order_id=row[0], proposal_id=row[1], source_review_id=row[2],
            source_inspection_work_order_id=row[3], road_code=row[4], segment_index=row[5],
            zone_type=row[6], creation_recommendation=row[7], source_review_state=row[8],
            order_type=row[9], status=row[10], version=row[11], planning_rationale=row[12],
            creation_policy_version=row[13], data_status=row[14], location_status=row[15],
            source_evidence_status=row[16], team_assignment_status=row[17],
            equipment_assignment_status=row[18], weather_check_status=row[19],
            safety_check_status=row[20], requires_operational_approval=row[21],
            created_at=row[22],
            resource_plan_count=row[23], latest_resource_plan_id=row[24],
            latest_team_reference=row[25], latest_equipment_reference=row[26],
            latest_resource_plan_rationale=row[27], latest_resource_plan_created_at=row[28],
            resource_plan_state=(
                "candidate_resources_pending_validation" if row[24] else "not_planned"
            ),
        )


async def get_prepared_mowing_order_repository() -> PostgresPreparedMowingOrderRepository:
    settings = get_settings()
    return PostgresPreparedMowingOrderRepository(
        settings.database_url, settings.prepared_mowing_order_policy_version
    )


router = APIRouter(prefix="/v1/prepared-mowing-orders", tags=["prepared-mowing-orders"])


@router.post("", response_model=PreparedMowingOrderResponse)
async def create_prepared_mowing_order(
    request: PreparedMowingOrderRequest,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=8, max_length=200)
    ],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[
        PreparedMowingOrderRepository, Depends(get_prepared_mowing_order_repository)
    ],
) -> PreparedMowingOrderResponse:
    try:
        return await repository.create(
            actor=actor, idempotency_key=idempotency_key, request=request
        )
    except MowingOrderSourceNotFoundError:
        raise HTTPException(404, "Effective proposal review not found") from None
    except MowingOrderSourceDecisionError:
        raise HTTPException(409, "Effective review does not select mowing review") from None
    except MowingOrderPermissionError:
        raise HTTPException(403, "Creator cannot prepare mowing orders for this road") from None
    except MowingOrderPolicyUnavailableError:
        raise HTTPException(503, "Prepared mowing-order policy is unavailable") from None
    except MowingOrderIdempotencyConflictError:
        raise HTTPException(409, "Idempotency-Key conflict") from None
    except MowingOrderAlreadyExistsError:
        raise HTTPException(409, "Effective review already has a prepared mowing order") from None


@router.get("", response_model=PreparedMowingOrderCollection)
async def list_prepared_mowing_orders(
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    repository: Annotated[
        PreparedMowingOrderRepository, Depends(get_prepared_mowing_order_repository)
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PreparedMowingOrderCollection:
    return await repository.list_for_actor(actor=actor, limit=limit)
