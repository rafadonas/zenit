import asyncio
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from zenit_api.main import app
from zenit_api.recommendations import (
    RecommendationQueue,
    RecommendationQueueItem,
    RecommendationQueueMetadata,
    get_recommendation_queue_reader,
)


class FakeQueueReader:
    async def list_pending(self, *, limit: int) -> RecommendationQueue:
        assert limit == 10
        return RecommendationQueue(
            items=[
                RecommendationQueueItem(
                    vegetation_analysis_id=UUID("00000000-0000-4000-8000-000000000001"),
                    analysis_run_id=UUID("00000000-0000-4000-8000-000000000002"),
                    segment_id=UUID("00000000-0000-4000-8000-000000000003"),
                    road_code="SP021",
                    segment_index=195,
                    zone_type="left",
                    zone_data_status="prepared",
                    acquired_at="2026-07-29T13:00:00+00:00",
                    recommendation="inspect",
                    conclusion="inconclusive",
                    confidence_band="low",
                    explanation={"input_data_status": "prepared"},
                    rule_version="satellite-quality-v1",
                    processor_version="sentinel-ndvi-v1",
                    requires_human_approval=True,
                    eligible_for_official_reporting=False,
                    review_count=0,
                    latest_review_id=None,
                    latest_review_decision=None,
                    latest_review_adjusted_recommendation=None,
                    latest_reviewed_at=None,
                    latest_review_policy_version=None,
                    latest_review_policy_data_status=None,
                    prepared_inspection_order_id=None,
                    review_state="awaiting_review",
                )
            ],
            metadata=RecommendationQueueMetadata(
                result_count=1,
                total_count=1,
                limit=10,
                truncated=False,
                warning="A recorded review is not field-work authorization.",
            ),
        )


def test_queue_is_read_only_and_never_authorizes_field_work() -> None:
    async def fake_reader() -> FakeQueueReader:
        return FakeQueueReader()

    async def request():
        app.dependency_overrides[get_recommendation_queue_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/v1/recommendations?limit=10")
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["review_state"] == "awaiting_review"
    assert item["recommendation"] == "inspect"
    assert item["authorizes_field_work"] is False
    assert item["eligible_for_official_reporting"] is False
    assert "reviewer_subject" not in item


def test_queue_rejects_out_of_range_limit() -> None:
    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/v1/recommendations?limit=101")

    assert asyncio.run(request()).status_code == 422
