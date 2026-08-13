import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mowing_post_service_exceptions import (
    ExceptionAlreadyExists,
    ExceptionForbidden,
    ExceptionIdempotencyConflict,
    ExceptionNotFound,
    ExceptionPolicyUnavailable,
    ExceptionReviewSupersession,
    MowingPostServiceExceptionCollection,
    MowingPostServiceExceptionRepository,
    MowingPostServiceExceptionRequest,
    MowingPostServiceExceptionResponse,
    MowingPostServiceExceptionReviewRequest,
    MowingPostServiceExceptionReviewResponse,
    get_exception_repository,
)

SUMMARY_ID = UUID("99000000-0000-4000-8000-000000000001")
EXCEPTION_ID = UUID("99000000-0000-4000-8000-000000000002")
MOWING_ORDER_ID = UUID("99000000-0000-4000-8000-000000000003")
REVIEW_ID = UUID("99000000-0000-4000-8000-000000000005")
ACTOR = AuthenticatedUser(
    id=UUID("99000000-0000-4000-8000-000000000004"),
    email="manager@example.test",
    display_name="Manager",
)


def exception_response() -> MowingPostServiceExceptionResponse:
    return MowingPostServiceExceptionResponse(
        exception_id=EXCEPTION_ID,
        summary_id=SUMMARY_ID,
        mowing_order_id=MOWING_ORDER_ID,
        road_code="SP-021",
        segment_index=195,
        zone_type="special",
        policy_version="prepared-mowing-post-service-exception-v1",
        creation_rationale="Avaliar pós-serviço simulado",
        recommendation="inspect_follow_up",
        applicable_threshold_cm=Decimal("10"),
        maximum_height_cm=Decimal("12"),
        threshold_exceeded=True,
        created_at=datetime(2026, 8, 13, 12, tzinfo=UTC),
    )


class FakeRepository(MowingPostServiceExceptionRepository):
    def __init__(self, failure: type[Exception] | None = None):
        self.failure = failure

    async def create(self, **values):
        if self.failure:
            raise self.failure
        assert values["summary_id"] == SUMMARY_ID
        assert values["actor"] == ACTOR
        assert values["idempotency_key"] == "exception-key-0001"
        request = values["request"]
        assert isinstance(request, MowingPostServiceExceptionRequest)
        assert request.creation_rationale == "Avaliar pós-serviço simulado"
        return exception_response()

    async def list_for_actor(self, **values):
        assert values == {"actor": ACTOR, "limit": 9}
        return MowingPostServiceExceptionCollection(
            items=[exception_response()], result_count=1, limit=9, truncated=False
        )

    async def record_review(self, **values):
        if self.failure:
            raise self.failure
        assert values["exception_id"] == EXCEPTION_ID
        assert values["actor"] == ACTOR
        assert values["idempotency_key"] == "exception-review-0001"
        request = values["request"]
        assert isinstance(request, MowingPostServiceExceptionReviewRequest)
        return MowingPostServiceExceptionReviewResponse(
            review_id=REVIEW_ID,
            exception_id=EXCEPTION_ID,
            decision=request.decision,
            adjusted_recommendation=request.adjusted_recommendation,
            rationale=request.rationale,
            supersedes_review_id=request.supersedes_review_id,
            policy_version="prepared-mowing-post-service-exception-v1",
            reviewed_at=datetime(2026, 8, 13, 13, tzinfo=UTC),
        )


def request_creation(failure: type[Exception] | None = None, payload=None, authenticated=True):
    async def actor():
        return ACTOR

    async def repository():
        return FakeRepository(failure)

    async def execute():
        if authenticated:
            app.dependency_overrides[get_current_user] = actor
        app.dependency_overrides[get_exception_repository] = repository
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.post(
                    f"/v1/prepared-mowing-post-service-summaries/{SUMMARY_ID}/exceptions",
                    headers={"Idempotency-Key": "exception-key-0001"},
                    json=payload or {
                        "creation_rationale": "  Avaliar pós-serviço simulado  "
                    },
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(execute())


def request_review(failure: type[Exception] | None = None, payload=None, authenticated=True):
    async def actor():
        return ACTOR

    async def repository():
        return FakeRepository(failure)

    async def execute():
        if authenticated:
            app.dependency_overrides[get_current_user] = actor
        app.dependency_overrides[get_exception_repository] = repository
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.post(
                    f"/v1/prepared-mowing-post-service-exceptions/{EXCEPTION_ID}/decisions",
                    headers={"Idempotency-Key": "exception-review-0001"},
                    json=payload or {"decision": "accepted"},
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(execute())


def test_exception_recommends_follow_up_without_authorizing_work():
    response = request_creation()
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation"] == "inspect_follow_up"
    assert payload["applicable_threshold_cm"] == "10"
    assert payload["threshold_exceeded"] is True
    assert payload["requires_human_review"] is True
    assert payload["data_status"] == "simulated"
    assert payload["location_status"] == "not_collected"
    assert payload["eligible_for_model_training"] is False
    assert payload["eligible_for_official_reporting"] is False
    assert payload["authorizes_field_work"] is False


def test_records_exception_review_without_authorizing_work():
    response = request_review()
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_id"] == str(REVIEW_ID)
    assert payload["decision"] == "accepted"
    assert payload["phase"] == "post_service"
    assert payload["data_status"] == "simulated"
    assert payload["eligible_for_official_reporting"] is False
    assert payload["authorizes_field_work"] is False


def test_adjusted_exception_review_requires_replacement_and_rationale():
    response = request_review(payload={"decision": "adjusted"})
    assert response.status_code == 422
    response = request_review(
        payload={
            "decision": "adjusted",
            "adjusted_recommendation": "monitor",
            "rationale": "Área especial deve ser monitorada no ensaio.",
        }
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "adjusted"
    assert payload["adjusted_recommendation"] == "monitor"


def test_rejected_exception_review_requires_rationale():
    assert request_review(payload={"decision": "rejected"}).status_code == 422
    response = request_review(
        payload={
            "decision": "rejected",
            "rationale": "Medição simulada digitada em ponto incorreto.",
        }
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "rejected"


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (ExceptionNotFound, 404),
        (ExceptionForbidden, 403),
        (ExceptionPolicyUnavailable, 503),
        (ExceptionAlreadyExists, 409),
        (ExceptionIdempotencyConflict, 409),
    ],
)
def test_exception_failures_have_stable_statuses(failure, status):
    assert request_creation(failure=failure).status_code == status


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (ExceptionNotFound, 404),
        (ExceptionForbidden, 403),
        (ExceptionIdempotencyConflict, 409),
        (ExceptionReviewSupersession, 409),
    ],
)
def test_exception_review_failures_have_stable_statuses(failure, status):
    assert request_review(failure=failure).status_code == status


def test_exception_requires_authentication_and_forbids_promotion_fields():
    assert request_creation(authenticated=False).status_code == 401
    response = request_creation(
        payload={
            "creation_rationale": "Avaliar pós-serviço simulado",
            "authorizes_field_work": True,
        }
    )
    assert response.status_code == 422


def test_exception_review_requires_authentication_and_forbids_promotion_fields():
    assert request_review(authenticated=False).status_code == 401
    response = request_review(
        payload={"decision": "accepted", "eligible_for_official_reporting": True}
    )
    assert response.status_code == 422


def test_lists_actor_scoped_simulated_exceptions():
    async def actor():
        return ACTOR

    async def repository():
        return FakeRepository()

    async def execute():
        app.dependency_overrides[get_current_user] = actor
        app.dependency_overrides[get_exception_repository] = repository
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.get(
                    "/v1/prepared-mowing-post-service-exceptions?limit=9"
                )
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(execute())
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["recommendation"] == "inspect_follow_up"
    assert payload["items"][0]["authorizes_field_work"] is False
    assert payload["warning"].startswith("Simulated post-service exceptions")
