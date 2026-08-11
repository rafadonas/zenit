import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.photo_reviews import (
    PhotoReviewIdempotencyConflictError,
    PhotoReviewPermissionError,
    PhotoReviewPolicyUnavailableError,
    PhotoReviewRequest,
    PhotoReviewResponse,
    PhotoReviewSupersessionError,
    PhotoReviewTargetNotFoundError,
    PhotoReviewWriter,
    get_photo_review_writer,
)

PHOTO_ID = UUID("40000000-0000-4000-8000-000000000007")
REVIEW_ID = UUID("40000000-0000-4000-8000-000000000008")
USER_ID = UUID("40000000-0000-4000-8000-000000000001")
ACTOR = AuthenticatedUser(
    id=USER_ID,
    email="manager@example.test",
    display_name="Prepared Manager",
)


class FakePhotoReviewWriter(PhotoReviewWriter):
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def record(
        self,
        *,
        photo_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        review: PhotoReviewRequest,
    ) -> PhotoReviewResponse:
        if self.failure is not None:
            raise self.failure
        assert photo_id == PHOTO_ID
        assert actor == ACTOR
        assert idempotency_key == "photo-review-0001"
        return PhotoReviewResponse(
            review_id=REVIEW_ID,
            photo_id=photo_id,
            decision=review.decision,
            quality_status=review.quality_status,
            ruler_status=review.ruler_status,
            rationale=review.rationale,
            supersedes_review_id=review.supersedes_review_id,
            review_policy_version="prepared-photo-review-v1",
            reviewed_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
        )


def request_review(payload: dict, failure: type[Exception] | None = None):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_writer() -> FakePhotoReviewWriter:
        return FakePhotoReviewWriter(failure)

    async def request():
        app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_photo_review_writer] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/media/{PHOTO_ID}/reviews",
                    headers={"Idempotency-Key": "photo-review-0001"},
                    json=payload,
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_accepted_review_remains_prepared_and_non_operational() -> None:
    response = request_review(
        {
            "decision": "accepted",
            "quality_status": "accepted",
            "ruler_status": "visible",
        }
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["review_policy_version"] == "prepared-photo-review-v1"
    assert payload["policy_data_status"] == "prepared"
    assert payload["eligible_for_field_evidence"] is False
    assert payload["eligible_for_model_training"] is False
    assert payload["eligible_for_official_reporting"] is False
    assert payload["authorizes_field_work"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {
            "decision": "accepted",
            "quality_status": "accepted",
            "ruler_status": "not_visible",
        },
        {
            "decision": "rejected",
            "quality_status": "rejected",
            "ruler_status": "not_visible",
        },
        {
            "decision": "inconclusive",
            "quality_status": "inconclusive",
            "ruler_status": "inconclusive",
            "reviewer_user_id": str(USER_ID),
            "rationale": "forged identity",
        },
    ],
)
def test_review_rejects_inconsistent_outcomes_missing_rationale_and_identity(payload: dict) -> None:
    assert request_review(payload).status_code == 422


def test_rejected_review_requires_and_normalizes_rationale() -> None:
    response = request_review(
        {
            "decision": "rejected",
            "quality_status": "rejected",
            "ruler_status": "not_visible",
            "rationale": "  Ruler is not visible.  ",
        }
    )

    assert response.status_code == 200
    assert response.json()["rationale"] == "Ruler is not visible."


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (PhotoReviewTargetNotFoundError, 404),
        (PhotoReviewPermissionError, 403),
        (PhotoReviewPolicyUnavailableError, 503),
        (PhotoReviewIdempotencyConflictError, 409),
        (PhotoReviewSupersessionError, 409),
    ],
)
def test_photo_review_failures_have_stable_statuses(
    failure: type[Exception], expected_status: int
) -> None:
    response = request_review(
        {
            "decision": "accepted",
            "quality_status": "accepted",
            "ruler_status": "visible",
        },
        failure,
    )

    assert response.status_code == expected_status


def test_photo_review_requires_authentication() -> None:
    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                f"/v1/media/{PHOTO_ID}/reviews",
                headers={"Idempotency-Key": "photo-review-0001"},
                json={
                    "decision": "accepted",
                    "quality_status": "accepted",
                    "ruler_status": "visible",
                },
            )

    assert asyncio.run(request()).status_code == 401
