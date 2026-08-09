from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["accepted", "rejected", "adjusted"]
    adjusted_recommendation: Literal["monitor", "inspect", "mowing_review"] | None = None
    rationale: str | None = Field(default=None, max_length=2000)
    supersedes_review_id: UUID | None = None

    @field_validator("rationale")
    @classmethod
    def normalize_rationale(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_decision_details(self) -> ReviewDecisionRequest:
        if (self.decision == "adjusted") != (self.adjusted_recommendation is not None):
            raise ValueError("adjusted decisions require exactly one adjusted recommendation")
        if self.decision in {"rejected", "adjusted"} and self.rationale is None:
            raise ValueError("rejected and adjusted decisions require a rationale")
        return self


class ReviewDecisionResponse(BaseModel):
    review_id: UUID
    vegetation_analysis_id: UUID
    decision: Literal["accepted", "rejected", "adjusted"]
    adjusted_recommendation: Literal["monitor", "inspect", "mowing_review"] | None
    rationale: str | None
    review_policy_version: str
    policy_data_status: Literal["prepared", "real"]
    dual_approval_required: bool
    reviewed_at: datetime
    authorizes_field_work: Literal[False] = False


class ReviewTargetNotFoundError(Exception):
    pass


class ReviewPermissionError(Exception):
    pass


class ReviewPolicyUnavailableError(Exception):
    pass


class ReviewIdempotencyConflictError(Exception):
    pass


class ReviewSupersessionError(Exception):
    pass


class RecommendationReviewWriter(Protocol):
    async def record(
        self,
        *,
        vegetation_analysis_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        decision: ReviewDecisionRequest,
    ) -> ReviewDecisionResponse: ...


class PostgresRecommendationReviewRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def record(
        self,
        *,
        vegetation_analysis_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        decision: ReviewDecisionRequest,
    ) -> ReviewDecisionResponse:
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            existing = await self._find_by_idempotency_key(cursor, key_hash)
            if existing is not None:
                self._assert_replay_matches(existing, vegetation_analysis_id, actor, decision)
                return self._response_from_row(existing)

            await cursor.execute(
                """
                SELECT axis.road_id
                FROM vegetation_analysis analysis
                JOIN segment_zone zone ON zone.id = analysis.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                WHERE analysis.id = %s
                """,
                (vegetation_analysis_id,),
            )
            target = await cursor.fetchone()
            if target is None:
                raise ReviewTargetNotFoundError

            await cursor.execute(
                """
                SELECT id, version, allowed_roles, data_status, dual_approval_required
                FROM recommendation_review_policy
                WHERE version = %s
                  AND requires_authenticated_identity
                  AND NOT authorizes_field_work
                """,
                (self._policy_version,),
            )
            policy = await cursor.fetchone()
            if policy is None:
                raise ReviewPolicyUnavailableError

            await cursor.execute(
                """
                SELECT role
                FROM road_user_role
                WHERE user_id = %s
                  AND road_id = %s
                  AND role = ANY(%s)
                ORDER BY CASE role WHEN 'manager' THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (actor.id, target[0], policy[2]),
            )
            assignment = await cursor.fetchone()
            if assignment is None:
                raise ReviewPermissionError

            if decision.supersedes_review_id is not None:
                await cursor.execute(
                    """
                    SELECT 1
                    FROM recommendation_review
                    WHERE id = %s AND vegetation_analysis_id = %s
                    """,
                    (decision.supersedes_review_id, vegetation_analysis_id),
                )
                if await cursor.fetchone() is None:
                    raise ReviewSupersessionError

            metadata = json.dumps(
                {
                    "actor_role": assignment[0],
                    "identity_source": "local_mvp",
                    "policy_data_status": policy[3],
                    "dual_approval_required": policy[4],
                    "authorizes_field_work": False,
                },
                sort_keys=True,
            )
            await cursor.execute(
                """
                INSERT INTO recommendation_review (
                    vegetation_analysis_id,
                    supersedes_review_id,
                    idempotency_key,
                    decision,
                    adjusted_recommendation,
                    rationale,
                    reviewer_subject,
                    source_channel,
                    review_metadata,
                    reviewed_at,
                    reviewer_user_id,
                    review_policy_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, 'api', %s::jsonb, now(), %s, %s
                )
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING
                    id,
                    vegetation_analysis_id,
                    decision,
                    adjusted_recommendation,
                    rationale,
                    reviewed_at,
                    reviewer_user_id,
                    supersedes_review_id,
                    review_policy_id
                """,
                (
                    vegetation_analysis_id,
                    decision.supersedes_review_id,
                    key_hash,
                    decision.decision,
                    decision.adjusted_recommendation,
                    decision.rationale,
                    str(actor.id),
                    metadata,
                    actor.id,
                    policy[0],
                ),
            )
            inserted = await cursor.fetchone()
            if inserted is None:
                existing = await self._find_by_idempotency_key(cursor, key_hash)
                if existing is None:
                    raise RuntimeError("idempotent review insert did not return a persisted row")
                self._assert_replay_matches(existing, vegetation_analysis_id, actor, decision)
                return self._response_from_row(existing)

            row = (*inserted, policy[1], policy[3], policy[4])
            return self._response_from_row(row)

    async def _find_by_idempotency_key(
        self,
        cursor: psycopg.AsyncCursor[tuple],
        key_hash: str,
    ) -> tuple | None:
        await cursor.execute(
            """
            SELECT
                review.id,
                review.vegetation_analysis_id,
                review.decision,
                review.adjusted_recommendation,
                review.rationale,
                review.reviewed_at,
                review.reviewer_user_id,
                review.supersedes_review_id,
                review.review_policy_id,
                policy.version,
                policy.data_status,
                policy.dual_approval_required
            FROM recommendation_review review
            LEFT JOIN recommendation_review_policy policy ON policy.id = review.review_policy_id
            WHERE review.idempotency_key = %s
            """,
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_replay_matches(
        row: tuple,
        vegetation_analysis_id: UUID,
        actor: AuthenticatedUser,
        decision: ReviewDecisionRequest,
    ) -> None:
        expected = (
            vegetation_analysis_id,
            decision.decision,
            decision.adjusted_recommendation,
            decision.rationale,
            actor.id,
            decision.supersedes_review_id,
        )
        actual = (row[1], row[2], row[3], row[4], row[6], row[7])
        if actual != expected or row[9] is None:
            raise ReviewIdempotencyConflictError

    @staticmethod
    def _response_from_row(row: tuple) -> ReviewDecisionResponse:
        return ReviewDecisionResponse(
            review_id=row[0],
            vegetation_analysis_id=row[1],
            decision=row[2],
            adjusted_recommendation=row[3],
            rationale=row[4],
            reviewed_at=row[5],
            review_policy_version=row[9],
            policy_data_status=row[10],
            dual_approval_required=row[11],
        )


async def get_recommendation_review_writer() -> RecommendationReviewWriter:
    settings = get_settings()
    return PostgresRecommendationReviewRepository(
        settings.database_url,
        settings.recommendation_review_policy_version,
    )


router = APIRouter(prefix="/v1/recommendations", tags=["recommendations"])


@router.post("/{vegetation_analysis_id}/decisions", response_model=ReviewDecisionResponse)
async def record_recommendation_decision(
    vegetation_analysis_id: UUID,
    decision: ReviewDecisionRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=200),
    ],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[
        RecommendationReviewWriter,
        Depends(get_recommendation_review_writer),
    ],
) -> ReviewDecisionResponse:
    try:
        return await writer.record(
            vegetation_analysis_id=vegetation_analysis_id,
            actor=actor,
            idempotency_key=idempotency_key,
            decision=decision,
        )
    except ReviewTargetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        ) from None
    except ReviewPermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer lacks the required role for this road",
        ) from None
    except ReviewPolicyUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation review policy is unavailable",
        ) from None
    except ReviewIdempotencyConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used for a different decision",
        ) from None
    except ReviewSupersessionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Superseded review must belong to the same recommendation",
        ) from None
