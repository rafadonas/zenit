from __future__ import annotations

from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator

from zenit_api.config import get_settings


class RecommendationQueueItem(BaseModel):
    vegetation_analysis_id: UUID
    analysis_run_id: UUID
    segment_id: UUID
    road_code: str
    segment_index: int = Field(ge=0)
    zone_type: Literal["left", "right", "median", "special"]
    zone_data_status: str
    acquired_at: str
    recommendation: Literal["monitor", "inspect", "mowing_review"]
    conclusion: Literal["conclusive", "inconclusive"]
    confidence_band: Literal["low", "medium", "high"]
    explanation: dict[str, Any]
    rule_version: str
    processor_version: str
    requires_human_approval: bool
    eligible_for_official_reporting: bool
    review_count: int = Field(ge=0)
    latest_review_id: UUID | None
    latest_review_decision: Literal["accepted", "rejected", "adjusted"] | None
    latest_review_adjusted_recommendation: Literal[
        "monitor", "inspect", "mowing_review"
    ] | None
    latest_reviewed_at: str | None
    latest_review_policy_version: str | None
    latest_review_policy_data_status: Literal["prepared", "real"] | None
    prepared_inspection_order_id: UUID | None
    review_state: Literal[
        "awaiting_review",
        "review_recorded_policy_pending",
        "review_recorded_no_work_authorization",
    ]
    authorizes_field_work: Literal[False] = False

    @model_validator(mode="after")
    def require_consistent_review_provenance(self) -> RecommendationQueueItem:
        if self.review_count == 0:
            if any(
                value is not None
                for value in (
                    self.latest_review_decision,
                    self.latest_review_id,
                    self.latest_review_adjusted_recommendation,
                    self.latest_reviewed_at,
                    self.latest_review_policy_version,
                    self.latest_review_policy_data_status,
                    self.prepared_inspection_order_id,
                )
            ) or self.review_state != "awaiting_review":
                raise ValueError("an unreviewed item cannot expose review metadata")
            return self

        if (
            self.latest_review_id is None
            or self.latest_review_decision is None
            or self.latest_reviewed_at is None
        ):
            raise ValueError("a reviewed item requires its latest event, decision, and timestamp")
        if (self.latest_review_decision == "adjusted") != (
            self.latest_review_adjusted_recommendation is not None
        ):
            raise ValueError("latest adjusted recommendation must match the latest decision")
        if self.latest_review_policy_version is None:
            if (
                self.latest_review_policy_data_status is not None
                or self.review_state != "review_recorded_policy_pending"
            ):
                raise ValueError("an unversioned legacy review must remain policy pending")
        elif (
            self.latest_review_policy_data_status is None
            or self.review_state != "review_recorded_no_work_authorization"
        ):
            raise ValueError("a versioned review must retain its policy status")
        effective_action = (
            self.latest_review_adjusted_recommendation
            if self.latest_review_decision == "adjusted"
            else self.recommendation
            if self.latest_review_decision == "accepted"
            else None
        )
        if self.prepared_inspection_order_id is not None and effective_action != "inspect":
            raise ValueError("a prepared inspection order requires an effective inspect decision")
        return self


class RecommendationQueueMetadata(BaseModel):
    result_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    truncated: bool
    warning: str


class RecommendationQueue(BaseModel):
    items: list[RecommendationQueueItem]
    metadata: RecommendationQueueMetadata


class RecommendationQueueReader(Protocol):
    async def list_pending(self, *, limit: int) -> RecommendationQueue: ...


class PostgresRecommendationQueueRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def list_pending(self, *, limit: int) -> RecommendationQueue:
        query = """
            SELECT
                result.id,
                analysis.id,
                segment.id,
                road.code,
                segment.segment_index,
                zone.zone_type,
                zone.data_status,
                scene.acquired_at,
                result.recommendation,
                result.conclusion,
                result.confidence_band,
                result.explanation,
                analysis.rule_version,
                analysis.processor_version,
                result.requires_human_approval,
                result.eligible_for_official_reporting,
                COALESCE(reviews.review_count, 0),
                reviews.latest_review_id,
                reviews.latest_decision,
                reviews.latest_adjusted_recommendation,
                reviews.latest_reviewed_at,
                reviews.latest_policy_version,
                reviews.latest_policy_data_status,
                reviews.latest_prepared_inspection_order_id,
                COUNT(*) OVER ()
            FROM vegetation_analysis result
            JOIN analysis_run analysis ON analysis.id = result.analysis_run_id
            JOIN satellite_scene scene ON scene.id = analysis.satellite_scene_id
            JOIN segment_zone zone ON zone.id = result.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*) AS review_count,
                    (array_agg(
                        review.id
                        ORDER BY review.reviewed_at DESC, review.created_at DESC
                    ))[1] AS latest_review_id,
                    (array_agg(
                        review.decision
                        ORDER BY review.reviewed_at DESC, review.created_at DESC
                    ))[1]
                        AS latest_decision,
                    (array_agg(
                        review.adjusted_recommendation
                        ORDER BY review.reviewed_at DESC, review.created_at DESC
                    ))[1] AS latest_adjusted_recommendation,
                    MAX(review.reviewed_at) AS latest_reviewed_at,
                    (array_agg(
                        policy.version
                        ORDER BY review.reviewed_at DESC, review.created_at DESC
                    ))[1] AS latest_policy_version,
                    (array_agg(
                        policy.data_status
                        ORDER BY review.reviewed_at DESC, review.created_at DESC
                    ))[1] AS latest_policy_data_status,
                    (array_agg(
                        order_record.id
                        ORDER BY review.reviewed_at DESC, review.created_at DESC
                    ))[1] AS latest_prepared_inspection_order_id
                FROM recommendation_review review
                LEFT JOIN recommendation_review_policy policy
                    ON policy.id = review.review_policy_id
                LEFT JOIN work_order order_record ON order_record.source_review_id = review.id
                WHERE review.vegetation_analysis_id = result.id
            ) reviews ON true
            WHERE result.requires_human_approval
            ORDER BY scene.acquired_at DESC, result.created_at DESC
            LIMIT %s
        """
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(query, (limit,))
            rows = await cursor.fetchall()
        items = [
            RecommendationQueueItem(
                vegetation_analysis_id=row[0],
                analysis_run_id=row[1],
                segment_id=row[2],
                road_code=row[3],
                segment_index=row[4],
                zone_type=row[5],
                zone_data_status=row[6],
                acquired_at=row[7].isoformat(),
                recommendation=row[8],
                conclusion=row[9],
                confidence_band=row[10],
                explanation=row[11],
                rule_version=row[12],
                processor_version=row[13],
                requires_human_approval=row[14],
                eligible_for_official_reporting=row[15],
                review_count=row[16],
                latest_review_id=row[17],
                latest_review_decision=row[18],
                latest_review_adjusted_recommendation=row[19],
                latest_reviewed_at=row[20].isoformat() if row[20] is not None else None,
                latest_review_policy_version=row[21],
                latest_review_policy_data_status=row[22],
                prepared_inspection_order_id=row[23],
                review_state=(
                    "awaiting_review"
                    if row[16] == 0
                    else (
                        "review_recorded_policy_pending"
                        if row[21] is None
                        else "review_recorded_no_work_authorization"
                    )
                ),
            )
            for row in rows
        ]
        total_count = int(rows[0][24]) if rows else 0
        return RecommendationQueue(
            items=items,
            metadata=RecommendationQueueMetadata(
                result_count=len(items),
                total_count=total_count,
                limit=limit,
                truncated=total_count > len(items),
                warning=(
                    "A recorded review or prepared order is not field-work authorization; "
                    "validated operational sources and an approved execution policy remain "
                    "required."
                ),
            ),
        )


async def get_recommendation_queue_reader() -> RecommendationQueueReader:
    return PostgresRecommendationQueueRepository(get_settings().database_url)


router = APIRouter(prefix="/v1/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationQueue)
async def list_recommendations(
    reader: Annotated[RecommendationQueueReader, Depends(get_recommendation_queue_reader)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RecommendationQueue:
    return await reader.list_pending(limit=limit)
