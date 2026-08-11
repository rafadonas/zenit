from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import get_settings


class PhotoReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["accepted", "rejected", "inconclusive"]
    quality_status: Literal["accepted", "rejected", "inconclusive"]
    ruler_status: Literal["visible", "not_visible", "inconclusive"]
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
    def validate_outcome(self) -> PhotoReviewRequest:
        accepted_evidence = self.quality_status == "accepted" and self.ruler_status == "visible"
        if (self.decision == "accepted") != accepted_evidence:
            raise ValueError("accepted reviews require accepted quality and a visible ruler")
        if self.decision != "accepted" and self.rationale is None:
            raise ValueError("rejected and inconclusive reviews require a rationale")
        return self


class PhotoReviewResponse(BaseModel):
    review_id: UUID
    photo_id: UUID
    decision: Literal["accepted", "rejected", "inconclusive"]
    quality_status: Literal["accepted", "rejected", "inconclusive"]
    ruler_status: Literal["visible", "not_visible", "inconclusive"]
    rationale: str | None
    supersedes_review_id: UUID | None
    review_policy_version: str
    policy_data_status: Literal["prepared"] = "prepared"
    reviewed_at: datetime
    eligible_for_field_evidence: Literal[False] = False
    eligible_for_model_training: Literal[False] = False
    eligible_for_official_reporting: Literal[False] = False
    authorizes_field_work: Literal[False] = False


class PhotoReviewTargetNotFoundError(Exception):
    pass


class PhotoReviewPermissionError(Exception):
    pass


class PhotoReviewPolicyUnavailableError(Exception):
    pass


class PhotoReviewIdempotencyConflictError(Exception):
    pass


class PhotoReviewSupersessionError(Exception):
    pass


class PhotoReviewWriter(Protocol):
    async def record(
        self,
        *,
        photo_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        review: PhotoReviewRequest,
    ) -> PhotoReviewResponse: ...


class PostgresPhotoReviewRepository:
    def __init__(self, database_url: str, policy_version: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        self._policy_version = policy_version

    async def record(
        self,
        *,
        photo_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        review: PhotoReviewRequest,
    ) -> PhotoReviewResponse:
        key_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            existing = await self._find_existing(cursor, key_hash)
            if existing is not None:
                self._assert_replay(existing, photo_id, actor, review)
                return self._response(existing)

            await cursor.execute(
                """
                SELECT axis.road_id
                FROM prepared_photo_upload_receipt receipt
                JOIN prepared_field_photo_manifest manifest
                  ON manifest.photo_id = receipt.photo_id
                JOIN work_order order_record ON order_record.id = manifest.work_order_id
                JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
                JOIN road_segment segment ON segment.id = zone.road_segment_id
                JOIN road_axis_candidate axis
                  ON axis.id = segment.road_axis_candidate_id
                WHERE receipt.photo_id = %s
                  AND receipt.content_status = 'uploaded_unverified'
                  AND receipt.ruler_status = 'not_validated'
                  AND receipt.quality_status = 'prepared_unverified'
                  AND receipt.data_status = 'prepared'
                  AND NOT receipt.eligible_for_official_reporting
                """,
                (photo_id,),
            )
            target = await cursor.fetchone()
            if target is None:
                raise PhotoReviewTargetNotFoundError

            await cursor.execute(
                """
                SELECT id, version, allowed_roles, data_status
                FROM prepared_photo_review_policy
                WHERE version = %s
                  AND requires_authenticated_identity
                  AND NOT authorizes_field_work
                  AND data_status = 'prepared'
                """,
                (self._policy_version,),
            )
            policy = await cursor.fetchone()
            if policy is None:
                raise PhotoReviewPolicyUnavailableError

            await cursor.execute(
                """
                SELECT role
                FROM road_user_role
                WHERE user_id = %s
                  AND road_id = %s
                  AND role = ANY(%s)
                  AND data_status <> 'simulated'
                ORDER BY CASE role WHEN 'manager' THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (actor.id, target[0], policy[2]),
            )
            if await cursor.fetchone() is None:
                raise PhotoReviewPermissionError

            if review.supersedes_review_id is not None:
                await cursor.execute(
                    """
                    SELECT 1 FROM prepared_photo_human_review
                    WHERE id = %s AND photo_id = %s
                    """,
                    (review.supersedes_review_id, photo_id),
                )
                if await cursor.fetchone() is None:
                    raise PhotoReviewSupersessionError

            await cursor.execute(
                """
                INSERT INTO prepared_photo_human_review (
                    photo_id, supersedes_review_id, reviewer_user_id,
                    review_policy_id, idempotency_key, decision,
                    quality_status, ruler_status, rationale, source_channel,
                    data_status, eligible_for_field_evidence,
                    eligible_for_model_training, eligible_for_official_reporting,
                    authorizes_field_work
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, 'api',
                    'prepared', false, false, false, false
                )
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id, photo_id, decision, quality_status, ruler_status,
                          rationale, supersedes_review_id, reviewer_user_id,
                          review_policy_id, reviewed_at
                """,
                (
                    photo_id,
                    review.supersedes_review_id,
                    actor.id,
                    policy[0],
                    key_hash,
                    review.decision,
                    review.quality_status,
                    review.ruler_status,
                    review.rationale,
                ),
            )
            inserted = await cursor.fetchone()
            if inserted is None:
                existing = await self._find_existing(cursor, key_hash)
                if existing is None:
                    raise RuntimeError("idempotent photo review insert returned no row")
                self._assert_replay(existing, photo_id, actor, review)
                return self._response(existing)
            return self._response((*inserted, policy[1], policy[3]))

    async def _find_existing(self, cursor: psycopg.AsyncCursor[tuple], key_hash: str):
        await cursor.execute(
            """
            SELECT review.id, review.photo_id, review.decision,
                   review.quality_status, review.ruler_status, review.rationale,
                   review.supersedes_review_id, review.reviewer_user_id,
                   review.review_policy_id, review.reviewed_at,
                   policy.version, policy.data_status
            FROM prepared_photo_human_review review
            JOIN prepared_photo_review_policy policy ON policy.id = review.review_policy_id
            WHERE review.idempotency_key = %s
            """,
            (key_hash,),
        )
        return await cursor.fetchone()

    @staticmethod
    def _assert_replay(
        row: tuple,
        photo_id: UUID,
        actor: AuthenticatedUser,
        review: PhotoReviewRequest,
    ) -> None:
        expected = (
            photo_id,
            review.decision,
            review.quality_status,
            review.ruler_status,
            review.rationale,
            review.supersedes_review_id,
            actor.id,
        )
        if row[1:8] != expected:
            raise PhotoReviewIdempotencyConflictError

    @staticmethod
    def _response(row: tuple) -> PhotoReviewResponse:
        return PhotoReviewResponse(
            review_id=row[0],
            photo_id=row[1],
            decision=row[2],
            quality_status=row[3],
            ruler_status=row[4],
            rationale=row[5],
            supersedes_review_id=row[6],
            reviewed_at=row[9],
            review_policy_version=row[10],
            policy_data_status=row[11],
        )


async def get_photo_review_writer() -> PhotoReviewWriter:
    settings = get_settings()
    return PostgresPhotoReviewRepository(
        settings.database_url,
        settings.prepared_photo_review_policy_version,
    )


router = APIRouter(prefix="/v1/media", tags=["media"])


@router.post("/{photo_id}/reviews", response_model=PhotoReviewResponse)
async def record_photo_review(
    photo_id: UUID,
    review: PhotoReviewRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=200),
    ],
    actor: Annotated[AuthenticatedUser, Depends(get_current_user)],
    writer: Annotated[PhotoReviewWriter, Depends(get_photo_review_writer)],
) -> PhotoReviewResponse:
    try:
        return await writer.record(
            photo_id=photo_id,
            actor=actor,
            idempotency_key=idempotency_key,
            review=review,
        )
    except PhotoReviewTargetNotFoundError:
        raise HTTPException(status_code=404, detail="Prepared photo not found") from None
    except PhotoReviewPermissionError:
        raise HTTPException(status_code=403, detail="Reviewer lacks a role for this road") from None
    except PhotoReviewPolicyUnavailableError:
        raise HTTPException(status_code=503, detail="Photo review policy is unavailable") from None
    except PhotoReviewIdempotencyConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used for a different photo review",
        ) from None
    except PhotoReviewSupersessionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Superseded review must belong to the same photo",
        ) from None
