from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings

DataStatus = Literal["real", "estimated", "simulated", "prepared", "inconclusive"]
ZoneType = Literal["left", "right", "median", "special"]


class PreparedInspectionOrderRequest(BaseModel):
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


class PlannedInspectionPointResponse(BaseModel):
    planned_point_id: UUID
    sequence: int = Field(ge=1, le=3)
    position_fraction: float = Field(gt=0, lt=1)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    geometry_srid: Literal[4326] = 4326
    planning_method: Literal["segment_centerline_fraction"]
    data_status: DataStatus
    eligible_for_field_execution: Literal[False] = False


class PreparedInspectionOrderResponse(BaseModel):
    work_order_id: UUID
    source_review_id: UUID
    vegetation_analysis_id: UUID
    segment_zone_id: UUID
    road_code: str
    segment_index: int = Field(ge=0)
    zone_type: ZoneType
    order_type: Literal["inspection"]
    status: Literal["prepared"]
    version: Literal[1]
    planning_rationale: str
    creation_policy_version: str
    policy_data_status: Literal["prepared", "real"]
    order_data_status: Literal["prepared"]
    source_axis_data_status: DataStatus
    source_segment_data_status: DataStatus
    source_zone_data_status: DataStatus
    created_at: datetime
    planned_points: list[PlannedInspectionPointResponse]
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False

    @model_validator(mode="after")
    def require_exactly_three_ordered_non_operational_points(
        self,
    ) -> PreparedInspectionOrderResponse:
        if [point.sequence for point in self.planned_points] != [1, 2, 3]:
            raise ValueError("prepared inspection order requires three ordered points")
        if any(point.eligible_for_field_execution for point in self.planned_points):
            raise ValueError("prepared inspection points cannot be field executable")
        return self


class PreparedInspectionOrderListMetadata(BaseModel):
    result_count: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    warning: str


class PreparedInspectionOrderListResponse(BaseModel):
    items: list[PreparedInspectionOrderResponse]
    metadata: PreparedInspectionOrderListMetadata


class WorkOrderSourceNotFoundError(Exception):
    pass


class WorkOrderSourceDecisionError(Exception):
    pass


class WorkOrderPermissionError(Exception):
    pass


class WorkOrderPolicyUnavailableError(Exception):
    pass


class WorkOrderIdempotencyConflictError(Exception):
    pass


class WorkOrderAlreadyExistsError(Exception):
    pass


class PreparedInspectionOrderWriter(Protocol):
    async def create(
        self,
        *,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedInspectionOrderRequest,
    ) -> PreparedInspectionOrderResponse: ...


class PreparedInspectionOrderReader(Protocol):
    async def list_for_user(
        self,
        *,
        actor: AuthenticatedUser,
        limit: int,
    ) -> PreparedInspectionOrderListResponse: ...


class PostgresPreparedInspectionOrderRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def create(
        self,
        *,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedInspectionOrderRequest,
    ) -> PreparedInspectionOrderResponse:
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        try:
            async with connection, connection.cursor() as cursor:
                existing = await self._find_by_idempotency_key(cursor, key_hash)
                if existing is not None:
                    self._assert_replay_matches(existing, actor, request)
                    return await self._response_for_id(cursor, existing[0])

                target = await self._load_effective_source(cursor, request.source_review_id)
                if target is None:
                    raise WorkOrderSourceNotFoundError
                if target[7] is not None or target[8] != "inspect":
                    raise WorkOrderSourceDecisionError

                policy = await self._load_policy(cursor)
                if policy is None:
                    raise WorkOrderPolicyUnavailableError

                await cursor.execute(
                    """
                    SELECT assignment.role, assignment.data_status
                    FROM road_user_role assignment
                    WHERE assignment.user_id = %s
                      AND assignment.road_id = %s
                      AND assignment.role = ANY(%s)
                      AND assignment.data_status <> 'simulated'
                    ORDER BY CASE assignment.role WHEN 'manager' THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (actor.id, target[5], policy[2]),
                )
                assignment = await cursor.fetchone()
                if assignment is None:
                    raise WorkOrderPermissionError

                order_metadata = json.dumps(
                    {
                        "actor_role": assignment[0],
                        "actor_role_data_status": assignment[1],
                        "authorizes_field_work": False,
                        "planning_method": "segment_centerline_fraction",
                        "point_locations_are_operational": False,
                        "source_axis_data_status": target[9],
                        "source_segment_data_status": target[10],
                        "source_zone_data_status": target[11],
                    },
                    sort_keys=True,
                )
                await cursor.execute(
                    """
                    INSERT INTO work_order (
                        source_review_id,
                        segment_zone_id,
                        creation_policy_id,
                        created_by_user_id,
                        idempotency_key,
                        planning_rationale,
                        order_metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING id
                    """,
                    (
                        request.source_review_id,
                        target[2],
                        policy[0],
                        actor.id,
                        key_hash,
                        request.planning_rationale,
                        order_metadata,
                    ),
                )
                inserted = await cursor.fetchone()
                if inserted is None:
                    existing = await self._find_by_idempotency_key(cursor, key_hash)
                    if existing is None:
                        raise RuntimeError("idempotent order insert did not return a persisted row")
                    self._assert_replay_matches(existing, actor, request)
                    return await self._response_for_id(cursor, existing[0])

                work_order_id = inserted[0]
                await cursor.execute(
                    """
                    INSERT INTO work_order_planned_point (
                        work_order_id,
                        sequence,
                        position_fraction,
                        planned_geometry,
                        planning_method,
                        data_status
                    )
                    SELECT
                        %s,
                        fraction.ordinality::integer,
                        fraction.value,
                        ST_LineInterpolatePoint(segment.metric_geometry, fraction.value),
                        'segment_centerline_fraction',
                        segment.data_status
                    FROM segment_zone zone
                    JOIN road_segment segment ON segment.id = zone.road_segment_id
                    CROSS JOIN unnest(%s::double precision[]) WITH ORDINALITY
                        AS fraction(value, ordinality)
                    WHERE zone.id = %s
                    """,
                    (work_order_id, policy[3], target[2]),
                )
                return await self._response_for_id(cursor, work_order_id)
        except UniqueViolation as error:
            if error.diag.constraint_name == "work_order_source_review_id_key":
                raise WorkOrderAlreadyExistsError from None
            raise

    async def list_for_user(
        self,
        *,
        actor: AuthenticatedUser,
        limit: int,
    ) -> PreparedInspectionOrderListResponse:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT order_record.id
                FROM work_order order_record
                JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                WHERE EXISTS (
                    SELECT 1
                    FROM road_user_role assignment
                    WHERE assignment.user_id = %s
                      AND assignment.road_id = axis.road_id
                      AND assignment.role IN ('manager', 'supervisor')
                      AND assignment.data_status <> 'simulated'
                )
                ORDER BY order_record.created_at DESC, order_record.id
                LIMIT %s
                """,
                (actor.id, limit),
            )
            ids = [row[0] for row in await cursor.fetchall()]
            items = [await self._response_for_id(cursor, order_id) for order_id in ids]
        return PreparedInspectionOrderListResponse(
            items=items,
            metadata=PreparedInspectionOrderListMetadata(
                result_count=len(items),
                limit=limit,
                warning=(
                    "Prepared inspection orders and centerline points are not field-execution "
                    "authorization."
                ),
            ),
        )

    async def _load_effective_source(
        self,
        cursor: psycopg.AsyncCursor[tuple],
        source_review_id: UUID,
    ) -> tuple | None:
        await cursor.execute(
            """
            SELECT
                review.id,
                analysis.id,
                zone.id,
                road.code,
                segment.segment_index,
                axis.road_id,
                zone.zone_type,
                correction.id,
                CASE
                    WHEN review.decision = 'accepted' THEN analysis.recommendation
                    WHEN review.decision = 'adjusted' THEN review.adjusted_recommendation
                    ELSE NULL
                END AS effective_action,
                axis.data_status,
                segment.data_status,
                zone.data_status
            FROM recommendation_review review
            JOIN vegetation_analysis analysis ON analysis.id = review.vegetation_analysis_id
            JOIN segment_zone zone ON zone.id = analysis.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            LEFT JOIN recommendation_review correction
                ON correction.supersedes_review_id = review.id
            WHERE review.id = %s
              AND review.review_policy_id IS NOT NULL
            """,
            (source_review_id,),
        )
        return await cursor.fetchone()

    async def _load_policy(self, cursor: psycopg.AsyncCursor[tuple]) -> tuple | None:
        await cursor.execute(
            """
            SELECT id, version, allowed_roles, planned_point_fractions, data_status
            FROM inspection_order_policy
            WHERE version = %s
              AND NOT authorizes_field_work
              AND data_status = 'prepared'
            """,
            (self._policy_version,),
        )
        return await cursor.fetchone()

    async def _find_by_idempotency_key(
        self,
        cursor: psycopg.AsyncCursor[tuple],
        key_hash: str,
    ) -> tuple | None:
        await cursor.execute(
            """
            SELECT id, source_review_id, created_by_user_id, planning_rationale
            FROM work_order
            WHERE idempotency_key = %s
            """,
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_replay_matches(
        row: tuple,
        actor: AuthenticatedUser,
        request: PreparedInspectionOrderRequest,
    ) -> None:
        if (row[1], row[2], row[3]) != (
            request.source_review_id,
            actor.id,
            request.planning_rationale,
        ):
            raise WorkOrderIdempotencyConflictError

    async def _response_for_id(
        self,
        cursor: psycopg.AsyncCursor[tuple],
        work_order_id: UUID,
    ) -> PreparedInspectionOrderResponse:
        await cursor.execute(
            """
            SELECT
                order_record.id,
                review.id,
                analysis.id,
                zone.id,
                road.code,
                segment.segment_index,
                zone.zone_type,
                order_record.order_type,
                order_record.status,
                order_record.version,
                order_record.planning_rationale,
                policy.version,
                policy.data_status,
                order_record.data_status,
                axis.data_status,
                segment.data_status,
                zone.data_status,
                order_record.created_at
            FROM work_order order_record
            JOIN recommendation_review review ON review.id = order_record.source_review_id
            JOIN vegetation_analysis analysis ON analysis.id = review.vegetation_analysis_id
            JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            JOIN inspection_order_policy policy ON policy.id = order_record.creation_policy_id
            WHERE order_record.id = %s
            """,
            (work_order_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise WorkOrderSourceNotFoundError

        await cursor.execute(
            """
            SELECT
                point.id,
                point.sequence,
                point.position_fraction,
                ST_X(ST_Transform(point.planned_geometry, 4326)),
                ST_Y(ST_Transform(point.planned_geometry, 4326)),
                point.planning_method,
                point.data_status
            FROM work_order_planned_point point
            WHERE point.work_order_id = %s
            ORDER BY point.sequence
            """,
            (work_order_id,),
        )
        points = await cursor.fetchall()
        return PreparedInspectionOrderResponse(
            work_order_id=row[0],
            source_review_id=row[1],
            vegetation_analysis_id=row[2],
            segment_zone_id=row[3],
            road_code=row[4],
            segment_index=row[5],
            zone_type=row[6],
            order_type=row[7],
            status=row[8],
            version=row[9],
            planning_rationale=row[10],
            creation_policy_version=row[11],
            policy_data_status=row[12],
            order_data_status=row[13],
            source_axis_data_status=row[14],
            source_segment_data_status=row[15],
            source_zone_data_status=row[16],
            created_at=row[17],
            planned_points=[
                PlannedInspectionPointResponse(
                    planned_point_id=point[0],
                    sequence=point[1],
                    position_fraction=point[2],
                    longitude=point[3],
                    latitude=point[4],
                    planning_method=point[5],
                    data_status=point[6],
                )
                for point in points
            ],
        )


async def get_prepared_inspection_order_repository() -> (
    PostgresPreparedInspectionOrderRepository
):
    settings = get_settings()
    return PostgresPreparedInspectionOrderRepository(
        settings.database_url,
        settings.inspection_order_policy_version,
    )


router = APIRouter(prefix="/v1/work-orders", tags=["work-orders"])


@router.post("", response_model=PreparedInspectionOrderResponse)
async def create_prepared_inspection_order(
    request: PreparedInspectionOrderRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=200),
    ],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[
        PreparedInspectionOrderWriter,
        Depends(get_prepared_inspection_order_repository),
    ],
) -> PreparedInspectionOrderResponse:
    try:
        return await writer.create(
            actor=actor,
            idempotency_key=idempotency_key,
            request=request,
        )
    except WorkOrderSourceNotFoundError:
        raise HTTPException(status_code=404, detail="Source review not found") from None
    except WorkOrderSourceDecisionError:
        raise HTTPException(
            status_code=409,
            detail="Source review is not the effective inspection decision",
        ) from None
    except WorkOrderPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Creator lacks the required role for this road",
        ) from None
    except WorkOrderPolicyUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="Prepared inspection-order policy is unavailable",
        ) from None
    except WorkOrderIdempotencyConflictError:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key was already used for a different order",
        ) from None
    except WorkOrderAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="The effective review already has a prepared inspection order",
        ) from None


@router.get("", response_model=PreparedInspectionOrderListResponse)
async def list_prepared_inspection_orders(
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reader: Annotated[
        PreparedInspectionOrderReader,
        Depends(get_prepared_inspection_order_repository),
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PreparedInspectionOrderListResponse:
    return await reader.list_for_user(actor=actor, limit=limit)
