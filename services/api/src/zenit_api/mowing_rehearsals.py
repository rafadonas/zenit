from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings

RehearsalState = Literal["not_started", "confirmed", "in_progress", "paused", "finished"]
REHEARSAL_HISTORY_WARNING = (
    "This history contains only a simulated mowing rehearsal and simulated, "
    "unverified typed post-service heights. It is not verified vegetation evidence, "
    "field execution, mowing efficacy, or official completion."
)


class PreparedMowingRehearsalEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_sequence: int = Field(ge=1)
    source_planning_approval_id: UUID
    operation: Literal["confirm", "start", "pause", "resume", "finish"]
    client_occurred_at: datetime
    location_status: Literal["not_collected", "simulated"]
    simulation_scope: Literal["demo_only"]
    rehearsal_scope: Literal["mowing_demo_rehearsal_only"]
    data_status: Literal["simulated"]
    operational_approval_satisfied: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False

    @model_validator(mode="after")
    def validate_location(self) -> PreparedMowingRehearsalEvent:
        expected = "simulated" if self.operation == "start" else "not_collected"
        if self.location_status != expected:
            raise ValueError("rehearsal event location does not match its operation")
        return self


class PreparedMowingPostServiceMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    source_planning_approval_id: UUID
    source_planned_point_id: UUID
    source_point_sequence: int = Field(ge=1, le=3)
    phase: Literal["post_service"]
    height_cm: Decimal = Field(ge=0, le=1000, max_digits=7, decimal_places=2)
    client_captured_at: datetime
    measurement_scope: Literal["mowing_demo_post_service_only"]
    location_status: Literal["not_collected"]
    photo_status: Literal["not_collected"]
    data_status: Literal["simulated"]
    quality_status: Literal["simulated_unverified"]
    evidence_claim_status: Literal["simulated_unverified_no_field_completion_claim"] = (
        "simulated_unverified_no_field_completion_claim"
    )
    operational_approval_satisfied: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False


@dataclass(frozen=True)
class RehearsalMetrics:
    state: RehearsalState
    event_count: int
    pause_count: int
    started_at: datetime | None
    finished_at: datetime | None
    recorded_span_seconds: float | None


def derive_rehearsal_metrics(
    events: list[PreparedMowingRehearsalEvent],
) -> RehearsalMetrics:
    previous: PreparedMowingRehearsalEvent | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pause_count = 0
    planning_approval_id: UUID | None = None

    for event in events:
        if planning_approval_id is None:
            planning_approval_id = event.source_planning_approval_id
        elif event.source_planning_approval_id != planning_approval_id:
            raise ValueError("rehearsal planning approval must remain stable")
        if previous is not None:
            if event.event_sequence <= previous.event_sequence:
                raise ValueError("rehearsal event sequence must increase")
            if event.client_occurred_at < previous.client_occurred_at:
                raise ValueError("rehearsal event time cannot move backwards")

        prior_operation = previous.operation if previous else None
        valid = (
            (event.operation == "confirm" and prior_operation is None)
            or (event.operation == "start" and prior_operation == "confirm")
            or (event.operation == "pause" and prior_operation in {"start", "resume"})
            or (event.operation == "resume" and prior_operation == "pause")
            or (event.operation == "finish" and prior_operation in {"start", "resume"})
        )
        if not valid:
            raise ValueError("invalid prepared mowing rehearsal sequence")
        if event.operation == "start":
            started_at = event.client_occurred_at
        elif event.operation == "pause":
            pause_count += 1
        elif event.operation == "finish":
            finished_at = event.client_occurred_at
        previous = event

    if previous is None:
        state: RehearsalState = "not_started"
    elif previous.operation == "confirm":
        state = "confirmed"
    elif previous.operation == "pause":
        state = "paused"
    elif previous.operation == "finish":
        state = "finished"
    else:
        state = "in_progress"

    last_timestamp = events[-1].client_occurred_at if events else None
    span = (
        (last_timestamp - started_at).total_seconds()
        if started_at is not None and last_timestamp is not None
        else None
    )
    return RehearsalMetrics(
        state=state,
        event_count=len(events),
        pause_count=pause_count,
        started_at=started_at,
        finished_at=finished_at,
        recorded_span_seconds=span,
    )


class PreparedMowingRehearsalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mowing_order_id: UUID
    road_code: str
    segment_index: int = Field(ge=0)
    zone_type: Literal["left", "right", "median", "special"]
    rehearsal_state: RehearsalState
    event_count: int = Field(ge=0)
    pause_count: int = Field(ge=0)
    started_at: datetime | None
    finished_at: datetime | None
    recorded_span_seconds: float | None = Field(default=None, ge=0)
    completion_claim_status: Literal["rehearsal_only_no_field_completion_claim"] = (
        "rehearsal_only_no_field_completion_claim"
    )
    data_status: Literal["simulated"] = "simulated"
    location_status: Literal["simulated"] = "simulated"
    operational_approval_satisfied: Literal[False] = False
    authorizes_field_work: Literal[False] = False
    eligible_for_field_execution: Literal[False] = False
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    events: list[PreparedMowingRehearsalEvent]
    post_service_measurements: list[PreparedMowingPostServiceMeasurement] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_derived_metrics(self) -> PreparedMowingRehearsalSummary:
        metrics = derive_rehearsal_metrics(self.events)
        actual = (
            self.rehearsal_state,
            self.event_count,
            self.pause_count,
            self.started_at,
            self.finished_at,
            self.recorded_span_seconds,
        )
        expected = (
            metrics.state,
            metrics.event_count,
            metrics.pause_count,
            metrics.started_at,
            metrics.finished_at,
            metrics.recorded_span_seconds,
        )
        if actual != expected:
            raise ValueError("rehearsal summary does not match its immutable events")
        measurements = self.post_service_measurements
        if len(measurements) > 3:
            raise ValueError("post-service measurement projection exceeds three points")
        sequences = [measurement.source_point_sequence for measurement in measurements]
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            raise ValueError("post-service measurements must be uniquely point-ordered")
        if len({measurement.event_id for measurement in measurements}) != len(measurements):
            raise ValueError("post-service measurement event IDs must be unique")
        if len({measurement.source_planned_point_id for measurement in measurements}) != len(
            measurements
        ):
            raise ValueError("post-service measurement source points must be unique")
        if measurements:
            if metrics.state != "finished" or metrics.finished_at is None:
                raise ValueError("post-service measurements require a finished rehearsal")
            planning_approval_ids = {event.source_planning_approval_id for event in self.events}
            if len(planning_approval_ids) != 1 or any(
                measurement.source_planning_approval_id not in planning_approval_ids
                for measurement in measurements
            ):
                raise ValueError(
                    "post-service measurements must match the rehearsal planning approval"
                )
            if any(
                measurement.client_captured_at < metrics.finished_at for measurement in measurements
            ):
                raise ValueError("post-service measurement cannot predate rehearsal finish")
        return self


class PreparedMowingRehearsalCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PreparedMowingRehearsalSummary]
    result_count: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    truncated: bool
    warning: Literal[
        "This history contains only a simulated mowing rehearsal and simulated, "
        "unverified typed post-service heights. It is not verified vegetation evidence, "
        "field execution, mowing efficacy, or official completion."
    ] = REHEARSAL_HISTORY_WARNING

    @model_validator(mode="after")
    def validate_result_count(self) -> PreparedMowingRehearsalCollection:
        if self.result_count != len(self.items):
            raise ValueError("rehearsal result count does not match returned items")
        return self


class PreparedMowingRehearsalReader(Protocol):
    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> PreparedMowingRehearsalCollection: ...


class PostgresPreparedMowingRehearsalReader:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def list_for_actor(
        self, *, actor: AuthenticatedUser, limit: int
    ) -> PreparedMowingRehearsalCollection:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT mowing.id, road.code, segment.segment_index, zone.zone_type,
                       inspection.id
                FROM prepared_mowing_order mowing
                JOIN work_order inspection
                  ON inspection.id = mowing.source_inspection_work_order_id
                JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis
                  ON axis.id = segment.road_axis_candidate_id
                JOIN road ON road.id = axis.road_id
                WHERE mowing.data_status = 'prepared'
                  AND mowing.status = 'prepared'
                  AND mowing.location_status = 'simulated'
                  AND mowing.source_evidence_status = 'prepared_reviewed_non_operational'
                  AND mowing.team_assignment_status = 'unassigned'
                  AND mowing.equipment_assignment_status = 'unassigned'
                  AND mowing.weather_check_status = 'pending'
                  AND mowing.safety_check_status = 'pending'
                  AND mowing.requires_operational_approval
                  AND NOT mowing.authorizes_field_work
                  AND NOT mowing.eligible_for_field_execution
                  AND NOT mowing.eligible_for_official_reporting
                  AND EXISTS (
                      SELECT 1 FROM road_user_role assignment
                      WHERE assignment.user_id = %s
                        AND assignment.road_id = axis.road_id
                        AND assignment.role IN ('manager', 'supervisor')
                        AND assignment.data_status <> 'simulated')
                ORDER BY mowing.created_at DESC, mowing.id
                LIMIT %s
                """,
                (actor.id, limit + 1),
            )
            targets = await cursor.fetchall()
            truncated = len(targets) > limit
            items = [await self._summary(cursor, target) for target in targets[:limit]]
        return PreparedMowingRehearsalCollection(
            items=items,
            result_count=len(items),
            limit=limit,
            truncated=truncated,
        )

    @staticmethod
    async def _summary(cursor, target) -> PreparedMowingRehearsalSummary:
        await cursor.execute(
            """
            SELECT event_id, event_sequence, source_planning_approval_id,
                   operation, client_occurred_at, location_status,
                   simulation_scope, rehearsal_scope, data_status,
                   operational_approval_satisfied, authorizes_field_work,
                   eligible_for_field_execution, eligible_for_model_training,
                   eligible_for_official_reporting
            FROM prepared_mowing_demo_event
            WHERE mowing_order_id = %s
            ORDER BY event_sequence
            """,
            (target[0],),
        )
        events = [
            PreparedMowingRehearsalEvent(
                event_id=row[0],
                event_sequence=row[1],
                source_planning_approval_id=row[2],
                operation=row[3],
                client_occurred_at=row[4],
                location_status=row[5],
                simulation_scope=row[6],
                rehearsal_scope=row[7],
                data_status=row[8],
                operational_approval_satisfied=row[9],
                authorizes_field_work=row[10],
                eligible_for_field_execution=row[11],
                eligible_for_model_training=row[12],
                eligible_for_official_reporting=row[13],
            )
            for row in await cursor.fetchall()
        ]
        await cursor.execute(
            """
            SELECT measurement.event_id,
                   measurement.source_planning_approval_id,
                   measurement.source_planned_point_id,
                   point.sequence,
                   point.work_order_id,
                   measurement.phase,
                   measurement.height_cm,
                   measurement.client_captured_at,
                   measurement.measurement_scope,
                   measurement.location_status,
                   measurement.photo_status,
                   measurement.data_status,
                   measurement.quality_status,
                   measurement.operational_approval_satisfied,
                   measurement.authorizes_field_work,
                   measurement.eligible_for_field_execution,
                   measurement.eligible_for_model_training,
                   measurement.eligible_for_official_reporting
            FROM prepared_mowing_post_service_measurement measurement
            JOIN work_order_planned_point point
              ON point.id = measurement.source_planned_point_id
            WHERE measurement.mowing_order_id = %s
            ORDER BY point.sequence, measurement.measurement_sequence
            """,
            (target[0],),
        )
        measurement_rows = await cursor.fetchall()
        if any(row[4] != target[4] for row in measurement_rows):
            raise ValueError("post-service measurement source order does not match")
        measurements = [
            PreparedMowingPostServiceMeasurement(
                event_id=row[0],
                source_planning_approval_id=row[1],
                source_planned_point_id=row[2],
                source_point_sequence=row[3],
                phase=row[5],
                height_cm=row[6],
                client_captured_at=row[7],
                measurement_scope=row[8],
                location_status=row[9],
                photo_status=row[10],
                data_status=row[11],
                quality_status=row[12],
                operational_approval_satisfied=row[13],
                authorizes_field_work=row[14],
                eligible_for_field_execution=row[15],
                eligible_for_model_training=row[16],
                eligible_for_official_reporting=row[17],
            )
            for row in measurement_rows
        ]
        metrics = derive_rehearsal_metrics(events)
        return PreparedMowingRehearsalSummary(
            mowing_order_id=target[0],
            road_code=target[1],
            segment_index=target[2],
            zone_type=target[3],
            rehearsal_state=metrics.state,
            event_count=metrics.event_count,
            pause_count=metrics.pause_count,
            started_at=metrics.started_at,
            finished_at=metrics.finished_at,
            recorded_span_seconds=metrics.recorded_span_seconds,
            events=events,
            post_service_measurements=measurements,
        )


async def get_prepared_mowing_rehearsal_reader() -> PostgresPreparedMowingRehearsalReader:
    return PostgresPreparedMowingRehearsalReader(get_settings().database_url)


router = APIRouter(
    prefix="/v1/prepared-mowing-rehearsals",
    tags=["prepared-mowing-orders"],
)


@router.get("", response_model=PreparedMowingRehearsalCollection)
async def list_prepared_mowing_rehearsals(
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    reader: Annotated[
        PreparedMowingRehearsalReader,
        Depends(get_prepared_mowing_rehearsal_reader),
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PreparedMowingRehearsalCollection:
    return await reader.list_for_actor(actor=actor, limit=limit)
