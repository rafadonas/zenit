import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.post_inspection_proposals import (
    PreparedProposalCollection,
    PreparedProposalReader,
    PreparedProposalRequest,
    PreparedProposalResponse,
    PreparedProposalReviewRequest,
    PreparedProposalReviewResponse,
    PreparedProposalReviewWriter,
    PreparedProposalWriter,
    ProposalAlreadyExistsError,
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalPermissionError,
    ProposalPolicyUnavailableError,
    ProposalReviewSupersessionError,
    get_prepared_proposal_repository,
)

SUMMARY_ID = UUID("60000000-0000-4000-8000-000000000001")
PROPOSAL_ID = UUID("60000000-0000-4000-8000-000000000002")
ORDER_ID = UUID("60000000-0000-4000-8000-000000000003")
ACTOR = AuthenticatedUser(
    id=UUID("60000000-0000-4000-8000-000000000004"),
    email="manager@example.test",
    display_name="Prepared Manager",
)


def proposal() -> PreparedProposalResponse:
    return PreparedProposalResponse(
        proposal_id=PROPOSAL_ID,
        summary_id=SUMMARY_ID,
        work_order_id=ORDER_ID,
        road_code="SP-021",
        segment_index=195,
        zone_type="special",
        policy_version="prepared-post-inspection-v1",
        creation_rationale="Aplicar regra preparada ao retorno revisado",
        recommendation="mowing_review",
        applicable_threshold_cm=Decimal("10"),
        maximum_height_cm=Decimal("35"),
        threshold_exceeded=True,
        created_at=datetime(2026, 8, 11, 17, tzinfo=UTC),
    )


class FakeProposalRepository(
    PreparedProposalWriter, PreparedProposalReader, PreparedProposalReviewWriter
):
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def create(self, **values) -> PreparedProposalResponse:
        if self.failure:
            raise self.failure
        assert values["summary_id"] == SUMMARY_ID
        assert values["actor"] == ACTOR
        assert values["idempotency_key"] == "proposal-attempt-0001"
        request: PreparedProposalRequest = values["request"]
        assert request.creation_rationale == "Aplicar regra preparada ao retorno revisado"
        return proposal()

    async def list_for_actor(self, **values) -> PreparedProposalCollection:
        assert values == {"actor": ACTOR, "limit": 7}
        return PreparedProposalCollection(
            items=[proposal()], result_count=1, limit=7, truncated=False
        )

    async def record_review(self, **values) -> PreparedProposalReviewResponse:
        if self.failure:
            raise self.failure
        assert values["proposal_id"] == PROPOSAL_ID
        assert values["actor"] == ACTOR
        assert values["idempotency_key"] == "proposal-review-0001"
        request: PreparedProposalReviewRequest = values["request"]
        return PreparedProposalReviewResponse(
            review_id=UUID("60000000-0000-4000-8000-000000000005"),
            proposal_id=PROPOSAL_ID,
            decision=request.decision,
            adjusted_recommendation=request.adjusted_recommendation,
            rationale=request.rationale,
            supersedes_review_id=request.supersedes_review_id,
            policy_version="prepared-post-inspection-v1",
            reviewed_at=datetime(2026, 8, 11, 18, tzinfo=UTC),
        )


def request_creation(
    failure: type[Exception] | None = None,
    authenticated: bool = True,
    payload: dict[str, object] | None = None,
):
    async def fake_actor():
        return ACTOR

    async def fake_repository():
        return FakeProposalRepository(failure)

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_proposal_repository] = fake_repository
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/prepared-inspection-summaries/{SUMMARY_ID}/post-inspection-proposal",
                    headers={"Idempotency-Key": "proposal-attempt-0001"},
                    json=payload or {
                        "creation_rationale": "  Aplicar regra preparada ao retorno revisado  "
                    },
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_proposal_preserves_threshold_and_all_human_safety_gates() -> None:
    response = request_creation()
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation"] == "mowing_review"
    assert payload["applicable_threshold_cm"] == "10"
    assert payload["maximum_height_cm"] == "35"
    assert payload["threshold_exceeded"] is True
    assert payload["requires_human_review"] is True
    assert payload["location_status"] == "simulated"
    assert payload["eligible_for_model_training"] is False
    assert payload["eligible_for_official_reporting"] is False
    assert payload["authorizes_field_work"] is False


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (ProposalNotFoundError, 404),
        (ProposalPermissionError, 403),
        (ProposalPolicyUnavailableError, 503),
        (ProposalIdempotencyConflictError, 409),
        (ProposalAlreadyExistsError, 409),
    ],
)
def test_proposal_failures_have_stable_statuses(failure: type[Exception], status: int) -> None:
    assert request_creation(failure).status_code == status


def test_proposal_requires_authentication_and_forbids_promotion_fields() -> None:
    assert request_creation(authenticated=False).status_code == 401
    assert request_creation(payload={
        "creation_rationale": "Aplicar regra preparada ao retorno revisado",
        "authorizes_field_work": True,
    }).status_code == 422


def test_lists_only_actor_scoped_prepared_proposals() -> None:
    async def fake_actor():
        return ACTOR

    async def fake_repository():
        return FakeProposalRepository()

    async def request():
        app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_proposal_repository] = fake_repository
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/v1/prepared-post-inspection-proposals?limit=7")
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.json()["items"][0]["requires_human_review"] is True


def test_proposal_collection_requires_authentication() -> None:
    async def fake_repository():
        return FakeProposalRepository()

    async def request():
        app.dependency_overrides[get_prepared_proposal_repository] = fake_repository
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/v1/prepared-post-inspection-proposals")
        finally:
            app.dependency_overrides.clear()

    assert asyncio.run(request()).status_code == 401


def request_review(
    failure: type[Exception] | None = None,
    authenticated: bool = True,
    payload: dict[str, object] | None = None,
):
    async def fake_actor():
        return ACTOR

    async def fake_repository():
        return FakeProposalRepository(failure)

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_proposal_repository] = fake_repository
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/prepared-post-inspection-proposals/{PROPOSAL_ID}/decisions",
                    headers={"Idempotency-Key": "proposal-review-0001"},
                    json=payload or {"decision": "accepted"},
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_review_records_human_decision_without_authorizing_mowing() -> None:
    response = request_review()
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "accepted"
    assert payload["data_status"] == "prepared"
    assert payload["eligible_for_official_reporting"] is False
    assert payload["authorizes_field_work"] is False


def test_review_requires_consistent_adjustment_and_rationale() -> None:
    assert request_review(payload={"decision": "adjusted"}).status_code == 422
    assert request_review(payload={
        "decision": "adjusted", "adjusted_recommendation": "monitor",
        "rationale": "Manter em observação no cenário preparado",
    }).status_code == 200
    assert request_review(payload={"decision": "rejected"}).status_code == 422


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (ProposalNotFoundError, 404),
        (ProposalPermissionError, 403),
        (ProposalIdempotencyConflictError, 409),
        (ProposalReviewSupersessionError, 409),
    ],
)
def test_review_failures_have_stable_statuses(failure: type[Exception], status: int) -> None:
    assert request_review(failure).status_code == status


def test_review_requires_authentication_and_forbids_authorization_fields() -> None:
    assert request_review(authenticated=False).status_code == 401
    assert request_review(payload={
        "decision": "accepted", "authorizes_field_work": True,
    }).status_code == 422
