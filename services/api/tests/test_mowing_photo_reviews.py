import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mowing_photo_reviews import (
    MowingPhotoReviewQueue,
    MowingPhotoReviewQueueItem,
    MowingPhotoReviewQueueReader,
    MowingPhotoReviewResponse,
    MowingPhotoReviewWriter,
    get_mowing_photo_review_queue_reader,
    get_mowing_photo_review_writer,
)
from zenit_api.photo_reviews import (
    PhotoReviewIdempotencyConflictError,
    PhotoReviewPermissionError,
    PhotoReviewPolicyUnavailableError,
    PhotoReviewRequest,
    PhotoReviewSupersessionError,
    PhotoReviewTargetNotFoundError,
)

PHOTO_ID = UUID("41000000-0000-4000-8000-000000000007")
REVIEW_ID = UUID("41000000-0000-4000-8000-000000000008")
USER_ID = UUID("41000000-0000-4000-8000-000000000001")
MOWING_ORDER_ID = UUID("41000000-0000-4000-8000-000000000009")
INSPECTION_ORDER_ID = UUID("41000000-0000-4000-8000-000000000010")
ACTOR = AuthenticatedUser(
    id=USER_ID,
    email="manager@example.test",
    display_name="Prepared Manager",
)


class FakeMowingPhotoReviewWriter(MowingPhotoReviewWriter):
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def record(
        self,
        *,
        photo_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        review: PhotoReviewRequest,
    ) -> MowingPhotoReviewResponse:
        if self.failure is not None:
            raise self.failure
        assert photo_id == PHOTO_ID
        assert actor == ACTOR
        assert idempotency_key == "mowing-photo-review-0001"
        return MowingPhotoReviewResponse(
            review_id=REVIEW_ID,
            photo_id=photo_id,
            decision=review.decision,
            quality_status=review.quality_status,
            ruler_status=review.ruler_status,
            rationale=review.rationale,
            supersedes_review_id=review.supersedes_review_id,
            review_policy_version="prepared-mowing-post-service-photo-review-v1",
            reviewed_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
        )


def request_review(
    payload: dict,
    failure: type[Exception] | None = None,
    *,
    authenticated: bool = True,
):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_writer() -> FakeMowingPhotoReviewWriter:
        return FakeMowingPhotoReviewWriter(failure)

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_mowing_photo_review_writer] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/mowing-media/{PHOTO_ID}/reviews",
                    headers={"Idempotency-Key": "mowing-photo-review-0001"},
                    json=payload,
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_accepted_review_remains_simulated_and_non_operational() -> None:
    response = request_review(
        {
            "decision": "accepted",
            "quality_status": "accepted",
            "ruler_status": "visible",
        }
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["review_policy_version"] == ("prepared-mowing-post-service-photo-review-v1")
    assert payload["phase"] == "post_service"
    assert payload["photo_scope"] == "mowing_demo_post_service_only"
    assert payload["location_status"] == "not_collected"
    assert payload["data_status"] == "simulated"
    assert payload["operational_approval_satisfied"] is False
    assert payload["eligible_for_field_evidence"] is False
    assert payload["eligible_for_field_execution"] is False
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
def test_review_rejects_inconsistent_outcomes_missing_rationale_and_identity(
    payload: dict,
) -> None:
    assert request_review(payload).status_code == 422


def test_rejected_review_requires_and_normalizes_rationale() -> None:
    response = request_review(
        {
            "decision": "rejected",
            "quality_status": "rejected",
            "ruler_status": "not_visible",
            "rationale": "  Image does not support review.  ",
        }
    )

    assert response.status_code == 200
    assert response.json()["rationale"] == "Image does not support review."


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
def test_review_failures_have_stable_statuses(
    failure: type[Exception],
    expected_status: int,
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


def test_review_requires_authentication() -> None:
    response = request_review(
        {
            "decision": "accepted",
            "quality_status": "accepted",
            "ruler_status": "visible",
        },
        authenticated=False,
    )
    assert response.status_code == 401


class FakeMowingPhotoReviewQueueReader(MowingPhotoReviewQueueReader):
    async def list_for_actor(
        self,
        *,
        actor: AuthenticatedUser,
        limit: int,
    ) -> MowingPhotoReviewQueue:
        assert actor == ACTOR
        assert limit == 25
        return MowingPhotoReviewQueue(
            items=[
                MowingPhotoReviewQueueItem(
                    photo_id=PHOTO_ID,
                    mowing_order_id=MOWING_ORDER_ID,
                    source_inspection_work_order_id=INSPECTION_ORDER_ID,
                    road_code="SP021",
                    segment_index=195,
                    zone_type="left",
                    planned_point_sequence=1,
                    captured_at=datetime(2026, 8, 12, 11, tzinfo=UTC),
                    uploaded_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
                    media_type="image/jpeg",
                    byte_size=4,
                    latest_review_id=None,
                    latest_decision=None,
                    latest_quality_status=None,
                    latest_ruler_status=None,
                    latest_rationale=None,
                    latest_reviewed_at=None,
                    latest_review_policy_version=None,
                    review_state="awaiting_review",
                )
            ],
            result_count=1,
            limit=25,
            truncated=False,
        )


def request_queue(*, authenticated: bool = True):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_reader() -> FakeMowingPhotoReviewQueueReader:
        return FakeMowingPhotoReviewQueueReader()

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_mowing_photo_review_queue_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/v1/mowing-photo-review-queue?limit=25")
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_queue_returns_only_simulated_non_operational_contract() -> None:
    response = request_queue()

    assert response.status_code == 200
    payload = response.json()
    assert payload["result_count"] == 1
    assert payload["items"][0]["review_state"] == "awaiting_review"
    assert payload["items"][0]["phase"] == "post_service"
    assert payload["items"][0]["data_status"] == "simulated"
    assert payload["items"][0]["eligible_for_field_evidence"] is False
    assert payload["items"][0]["eligible_for_model_training"] is False
    assert payload["items"][0]["eligible_for_official_reporting"] is False
    assert payload["items"][0]["authorizes_field_work"] is False
    assert "reviewer" not in response.text
    assert "device" not in response.text
    assert "object_" not in response.text


def test_queue_requires_authentication() -> None:
    assert request_queue(authenticated=False).status_code == 401
