import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.recommendation_reviews import (
    RecommendationReviewWriter,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewIdempotencyConflictError,
    ReviewPermissionError,
    ReviewPolicyUnavailableError,
    ReviewSupersessionError,
    ReviewTargetNotFoundError,
    get_recommendation_review_writer,
)

ANALYSIS_ID = UUID("20000000-0000-4000-8000-000000000001")
USER_ID = UUID("20000000-0000-4000-8000-000000000002")
REVIEW_ID = UUID("20000000-0000-4000-8000-000000000003")
ACTOR = AuthenticatedUser(
    id=USER_ID,
    email="manager@example.test",
    display_name="MVP Manager",
)


class FakeReviewWriter(RecommendationReviewWriter):
    def __init__(self, *, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def record(
        self,
        *,
        vegetation_analysis_id: UUID,
        actor: AuthenticatedUser,
        idempotency_key: str,
        decision: ReviewDecisionRequest,
    ) -> ReviewDecisionResponse:
        if self.failure is not None:
            raise self.failure
        assert vegetation_analysis_id == ANALYSIS_ID
        assert actor == ACTOR
        assert idempotency_key == "review-attempt-0001"
        return ReviewDecisionResponse(
            review_id=REVIEW_ID,
            vegetation_analysis_id=ANALYSIS_ID,
            decision=decision.decision,
            adjusted_recommendation=decision.adjusted_recommendation,
            rationale=decision.rationale,
            review_policy_version="recommendation-review-mvp-v1",
            policy_data_status="prepared",
            dual_approval_required=False,
            reviewed_at=datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
        )


def _request_with_overrides(
    payload: dict,
    *,
    failure: type[Exception] | None = None,
):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_writer() -> FakeReviewWriter:
        return FakeReviewWriter(failure=failure)

    async def request():
        app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_recommendation_review_writer] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/recommendations/{ANALYSIS_ID}/decisions",
                    headers={"Idempotency-Key": "review-attempt-0001"},
                    json=payload,
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_authenticated_decision_uses_server_actor_and_never_authorizes_work() -> None:
    response = _request_with_overrides({"decision": "accepted"})

    assert response.status_code == 200
    assert response.json() == {
        "review_id": str(REVIEW_ID),
        "vegetation_analysis_id": str(ANALYSIS_ID),
        "decision": "accepted",
        "adjusted_recommendation": None,
        "rationale": None,
        "review_policy_version": "recommendation-review-mvp-v1",
        "policy_data_status": "prepared",
        "dual_approval_required": False,
        "reviewed_at": "2026-08-08T12:00:00Z",
        "authorizes_field_work": False,
    }


def test_adjusted_decision_requires_rationale_and_replacement() -> None:
    response = _request_with_overrides({"decision": "adjusted"})

    assert response.status_code == 422


def test_decision_body_cannot_supply_reviewer_identity() -> None:
    response = _request_with_overrides(
        {"decision": "accepted", "reviewer_subject": "forged-actor"}
    )

    assert response.status_code == 422


def test_role_denial_is_enforced_by_the_server() -> None:
    response = _request_with_overrides(
        {"decision": "rejected", "rationale": "Not enough evidence"},
        failure=ReviewPermissionError,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Reviewer lacks the required role for this road"


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (ReviewTargetNotFoundError, 404),
        (ReviewPolicyUnavailableError, 503),
        (ReviewIdempotencyConflictError, 409),
        (ReviewSupersessionError, 409),
    ],
)
def test_domain_failures_have_stable_http_statuses(
    failure: type[Exception],
    expected_status: int,
) -> None:
    response = _request_with_overrides({"decision": "accepted"}, failure=failure)

    assert response.status_code == expected_status


def test_decision_endpoint_requires_bearer_authentication() -> None:
    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                f"/v1/recommendations/{ANALYSIS_ID}/decisions",
                headers={"Idempotency-Key": "review-attempt-0001"},
                json={"decision": "accepted"},
            )

    response = asyncio.run(request())

    assert response.status_code == 401
