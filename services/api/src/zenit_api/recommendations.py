from __future__ import annotations

from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from zenit_api.config import get_settings


class RecommendationQueueItem(BaseModel):
    vegetation_analysis_id: UUID
    analysis_run_id: UUID
    segment_id: UUID
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
    latest_review_decision: Literal["accepted", "rejected", "adjusted"] | None
    latest_reviewed_at: str | None
    review_state: Literal["awaiting_review", "review_recorded_policy_pending"]
    authorizes_field_work: Literal[False] = False


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
                reviews.latest_decision,
                reviews.latest_reviewed_at,
                COUNT(*) OVER ()
            FROM vegetation_analysis result
            JOIN analysis_run analysis ON analysis.id = result.analysis_run_id
            JOIN satellite_scene scene ON scene.id = analysis.satellite_scene_id
            JOIN segment_zone zone ON zone.id = result.segment_zone_id
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*) AS review_count,
                    (array_agg(
                        review.decision
                        ORDER BY review.reviewed_at DESC, review.created_at DESC
                    ))[1]
                        AS latest_decision,
                    MAX(review.reviewed_at) AS latest_reviewed_at
                FROM recommendation_review review
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
                segment_index=row[3],
                zone_type=row[4],
                zone_data_status=row[5],
                acquired_at=row[6].isoformat(),
                recommendation=row[7],
                conclusion=row[8],
                confidence_band=row[9],
                explanation=row[10],
                rule_version=row[11],
                processor_version=row[12],
                requires_human_approval=row[13],
                eligible_for_official_reporting=row[14],
                review_count=row[15],
                latest_review_decision=row[16],
                latest_reviewed_at=row[17].isoformat() if row[17] is not None else None,
                review_state=(
                    "awaiting_review" if row[15] == 0 else "review_recorded_policy_pending"
                ),
            )
            for row in rows
        ]
        total_count = int(rows[0][18]) if rows else 0
        return RecommendationQueue(
            items=items,
            metadata=RecommendationQueueMetadata(
                result_count=len(items),
                total_count=total_count,
                limit=limit,
                truncated=total_count > len(items),
                warning=(
                    "A recorded review is not field-work authorization; approval policy and "
                    "work-order linkage remain required."
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
