import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mowing_post_service_summaries import (
    MowingPostServiceSummaryCollection,
    MowingPostServiceSummaryResponse,
    MowingSummaryReader,
    MowingSummaryWriter,
    SummaryEvidenceIncomplete,
    get_mowing_summary_reader,
    get_mowing_summary_writer,
)

ORDER_ID = UUID("98000000-0000-4000-8000-000000000001")
SUMMARY_ID = UUID("98000000-0000-4000-8000-000000000002")
ACTOR = AuthenticatedUser(
    id=UUID("98000000-0000-4000-8000-000000000003"),
    email="manager@example.test",
    display_name="Manager",
)


class FakeWriter(MowingSummaryWriter):
    def __init__(self, failure=None):
        self.failure = failure

    async def create(self, **values):
        if self.failure:
            raise self.failure
        assert values["mowing_order_id"] == ORDER_ID
        return MowingPostServiceSummaryResponse(
            summary_id=SUMMARY_ID,
            mowing_order_id=ORDER_ID,
            summary_policy_version="prepared-mowing-post-service-summary-v1",
            generation_rationale=values["request"].generation_rationale,
            minimum_height_cm=Decimal("4.00"),
            maximum_height_cm=Decimal("8.00"),
            mean_height_cm=Decimal("6.0000"),
            n1_count=3,
            n2_count=0,
            n3_count=0,
            generated_at=datetime(2026, 8, 12, tzinfo=UTC),
        )


class FakeReader(MowingSummaryReader):
    async def list_for_actor(self, **values):
        assert values["actor"] == ACTOR
        assert values["limit"] == 12
        item = MowingPostServiceSummaryResponse(
            summary_id=SUMMARY_ID,
            mowing_order_id=ORDER_ID,
            summary_policy_version="prepared-mowing-post-service-summary-v1",
            generation_rationale="Consolidar retorno pós-serviço",
            minimum_height_cm=Decimal("4.00"),
            maximum_height_cm=Decimal("8.00"),
            mean_height_cm=Decimal("6.0000"),
            n1_count=3,
            n2_count=0,
            n3_count=0,
            generated_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        return MowingPostServiceSummaryCollection(
            items=[item], result_count=1, limit=12, truncated=False
        )


def request(payload, failure=None):
    async def actor():
        return ACTOR

    async def writer():
        return FakeWriter(failure)

    async def execute():
        app.dependency_overrides[get_current_user] = actor
        app.dependency_overrides[get_mowing_summary_writer] = writer
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.post(
                    f"/v1/prepared-mowing-orders/{ORDER_ID}/post-service-summary",
                    headers={"Idempotency-Key": "summary-key-0001"},
                    json=payload,
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(execute())


def test_summary_remains_simulated_and_non_operational():
    response = request({"generation_rationale": "  Consolidar retorno pós-serviço  "})
    assert response.status_code == 200
    payload = response.json()
    assert payload["generation_rationale"] == "Consolidar retorno pós-serviço"
    assert payload["phase"] == "post_service"
    assert payload["data_status"] == "simulated"
    assert payload["accepted_photo_review_count"] == 3
    assert payload["authorizes_field_work"] is False


def test_summary_rejects_extra_fields_and_incomplete_evidence():
    assert request({"generation_rationale": "ok", "minimum_height_cm": 1}).status_code == 422
    assert (
        request({"generation_rationale": "ok"}, SummaryEvidenceIncomplete).status_code == 409
    )


def test_list_summaries_keeps_simulated_safety_contract():
    async def actor():
        return ACTOR

    async def reader():
        return FakeReader()

    async def execute():
        app.dependency_overrides[get_current_user] = actor
        app.dependency_overrides[get_mowing_summary_reader] = reader
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.get(
                    "/v1/prepared-mowing-post-service-summaries?limit=12"
                )
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(execute())
    assert response.status_code == 200
    payload = response.json()
    assert payload["warning"].startswith("Resumo pós-serviço simulado")
    assert payload["items"][0]["data_status"] == "simulated"
    assert payload["items"][0]["eligible_for_official_reporting"] is False
    assert payload["items"][0]["authorizes_field_work"] is False
