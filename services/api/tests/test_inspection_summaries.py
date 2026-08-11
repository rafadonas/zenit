import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.inspection_summaries import (
    PreparedSummaryCollection,
    PreparedSummaryReader,
    PreparedSummaryRequest,
    PreparedSummaryResponse,
    PreparedSummaryWriter,
    SummaryAlreadyExistsError,
    SummaryEvidenceIncompleteError,
    SummaryIdempotencyConflictError,
    SummaryPermissionError,
    SummaryPolicyUnavailableError,
    SummaryTargetNotFoundError,
    get_prepared_summary_reader,
    get_prepared_summary_writer,
)
from zenit_api.main import app

ORDER_ID = UUID("50000000-0000-4000-8000-000000000001")
SUMMARY_ID = UUID("50000000-0000-4000-8000-000000000002")
ACTOR = AuthenticatedUser(
    id=UUID("50000000-0000-4000-8000-000000000003"),
    email="manager@example.test",
    display_name="Prepared Manager",
)


class FakeSummaryWriter(PreparedSummaryWriter):
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def create(self, **values) -> PreparedSummaryResponse:
        if self.failure:
            raise self.failure
        assert values["work_order_id"] == ORDER_ID
        assert values["actor"] == ACTOR
        assert values["idempotency_key"] == "summary-attempt-0001"
        request: PreparedSummaryRequest = values["request"]
        return PreparedSummaryResponse(
            summary_id=SUMMARY_ID,
            work_order_id=ORDER_ID,
            summary_policy_version="prepared-inspection-summary-v1",
            generation_rationale=request.generation_rationale,
            measurement_count=3,
            accepted_photo_review_count=3,
            minimum_height_cm=Decimal("8"),
            maximum_height_cm=Decimal("35"),
            mean_height_cm=Decimal("21.6667"),
            n1_count=1,
            n2_count=1,
            n3_count=1,
            generated_at=datetime(2026, 8, 11, 15, tzinfo=UTC),
        )


class FakeSummaryReader(PreparedSummaryReader):
    async def list_for_actor(self, **values) -> PreparedSummaryCollection:
        assert values == {"actor": ACTOR, "limit": 7}
        return PreparedSummaryCollection(
            items=[
                PreparedSummaryResponse(
                    summary_id=SUMMARY_ID,
                    work_order_id=ORDER_ID,
                    summary_policy_version="prepared-inspection-summary-v1",
                    generation_rationale="Consolidar retorno preparado",
                    measurement_count=3,
                    accepted_photo_review_count=3,
                    minimum_height_cm=Decimal("8"),
                    maximum_height_cm=Decimal("35"),
                    mean_height_cm=Decimal("21.6667"),
                    n1_count=1,
                    n2_count=1,
                    n3_count=1,
                    generated_at=datetime(2026, 8, 11, 15, tzinfo=UTC),
                )
            ],
            result_count=1,
            limit=7,
            truncated=False,
        )


def request_summary(failure: type[Exception] | None = None, authenticated: bool = True):
    async def fake_actor():
        return ACTOR

    async def fake_writer():
        return FakeSummaryWriter(failure)

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_summary_writer] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/work-orders/{ORDER_ID}/prepared-summary",
                    headers={"Idempotency-Key": "summary-attempt-0001"},
                    json={"generation_rationale": "  Consolidar retorno preparado  "},
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_summary_preserves_classes_and_all_safety_boundaries() -> None:
    response = request_summary()
    assert response.status_code == 200
    payload = response.json()
    assert (payload["n1_count"], payload["n2_count"], payload["n3_count"]) == (1, 1, 1)
    assert payload["class_rule"] == "N1 < 10 cm; N2 10-30 cm; N3 > 30 cm"
    assert payload["location_status"] == "simulated"
    assert payload["data_status"] == "prepared"
    assert payload["eligible_for_model_training"] is False
    assert payload["eligible_for_official_reporting"] is False
    assert payload["authorizes_field_work"] is False


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (SummaryTargetNotFoundError, 404),
        (SummaryPermissionError, 403),
        (SummaryPolicyUnavailableError, 503),
        (SummaryEvidenceIncompleteError, 409),
        (SummaryIdempotencyConflictError, 409),
        (SummaryAlreadyExistsError, 409),
    ],
)
def test_summary_failures_have_stable_statuses(failure: type[Exception], status: int) -> None:
    assert request_summary(failure).status_code == status


def test_summary_requires_authentication_and_forbids_extra_fields() -> None:
    assert request_summary(authenticated=False).status_code == 401


def test_lists_only_safe_prepared_summary_contract_for_authenticated_actor() -> None:
    async def fake_actor():
        return ACTOR

    async def fake_reader():
        return FakeSummaryReader()

    async def request():
        app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_summary_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/v1/prepared-inspection-summaries?limit=7")
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())
    assert response.status_code == 200
    payload = response.json()
    assert payload["result_count"] == 1
    summary = payload["items"][0]
    assert summary["location_status"] == "simulated"
    assert summary["eligible_for_official_reporting"] is False
    assert summary["authorizes_field_work"] is False
    assert "generated_by_user_id" not in summary


def test_summary_collection_requires_authentication() -> None:
    async def fake_reader():
        return FakeSummaryReader()

    async def request():
        app.dependency_overrides[get_prepared_summary_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/v1/prepared-inspection-summaries")
        finally:
            app.dependency_overrides.clear()

    assert asyncio.run(request()).status_code == 401
