import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.vegetation_cover import (
    VegetationCoverCollection,
    VegetationCoverMetadata,
    VegetationCoverObservation,
    VegetationCoverPermissionError,
    VegetationCoverSegmentNotFoundError,
    get_vegetation_cover_reader,
)

SEGMENT_ID = UUID("00000000-0000-0000-0000-000000000001")
ZONE_ID = UUID("00000000-0000-0000-0000-000000000002")
OBSERVATION_ID = UUID("00000000-0000-0000-0000-000000000003")
ACTOR = AuthenticatedUser(
    id=UUID("00000000-0000-0000-0000-000000000010"),
    email="manager@example.test",
    display_name="Manager",
)


class FakeReader:
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def by_segment(self, segment_id, *, actor, limit):
        assert segment_id == SEGMENT_ID
        assert actor == ACTOR
        assert limit == 10
        if self.failure is not None:
            raise self.failure
        return VegetationCoverCollection(
            items=[
                VegetationCoverObservation(
                    observation_id=OBSERVATION_ID,
                    segment_id=SEGMENT_ID,
                    segment_zone_id=ZONE_ID,
                    segment_index=7,
                    zone_type="left",
                    cover_type="unknown",
                    unknown_reason="shadow",
                    cover_type_method="model_estimated",
                    source_type="satellite",
                    source_reference="scene:planet-example-1",
                    source_acquired_at=datetime(2026, 8, 1, 12, tzinfo=UTC),
                    source_checksum_sha256="a" * 64,
                    validity_status="limited",
                    confidence_band="low",
                    quality_status="limited",
                    review_state="pending",
                    taxonomy_version="zenit-cover-taxonomy-v0.1-draft",
                    model_version="cover-baseline-v0",
                    coverage_band=None,
                    visibility="mostly_occluded",
                    dominance=None,
                    spatial_relation="inside_zone",
                    rationale="Shadow prevents a reliable cover classification.",
                    gps_status="simulated",
                    gps_accuracy_m=None,
                    data_status="prepared",
                    provenance={"source_status": "prepared", "lineage_id": "lineage-1"},
                    supersedes_observation_id=None,
                    reviewed_by_user_id=None,
                    reviewed_at=None,
                    created_at=datetime(2026, 8, 2, 12, tzinfo=UTC),
                )
            ],
            metadata=VegetationCoverMetadata(
                segment_id=SEGMENT_ID,
                result_count=1,
                total_count=3,
                limit=10,
                truncated=True,
                warning=(
                    "Cover type is versioned evidence, not vegetation height, current condition, "
                    "or authorization for mowing."
                ),
            ),
        )


def request(*, authenticated: bool = True, failure: type[Exception] | None = None):
    async def fake_actor():
        return ACTOR

    async def fake_reader():
        return FakeReader(failure)

    async def execute():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_vegetation_cover_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(
                    f"/v1/segments/{SEGMENT_ID}/vegetation-cover?limit=10"
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(execute())


def test_cover_endpoint_exposes_type_provenance_and_review_state() -> None:
    response = request()

    assert response.status_code == 200
    payload = response.json()
    item = payload["items"][0]
    assert item["cover_type"] == "unknown"
    assert item["unknown_reason"] == "shadow"
    assert item["cover_type_method"] == "model_estimated"
    assert item["source_reference"] == "scene:planet-example-1"
    assert item["validity_status"] == "limited"
    assert item["confidence_band"] == "low"
    assert item["quality_status"] == "limited"
    assert item["review_state"] == "pending"
    assert item["data_status"] == "prepared"
    assert item["eligible_for_official_reporting"] is False
    assert item["provenance"]["lineage_id"] == "lineage-1"
    assert payload["metadata"]["truncated"] is True


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (VegetationCoverPermissionError, 403),
        (VegetationCoverSegmentNotFoundError, 404),
    ],
)
def test_cover_endpoint_maps_scope_failures(failure: type[Exception], status: int) -> None:
    assert request(failure=failure).status_code == status


def test_cover_endpoint_requires_authentication() -> None:
    assert request(authenticated=False).status_code == 401


def test_cover_endpoint_rejects_invalid_uuid_and_limit() -> None:
    async def execute(path: str):
        async def fake_actor():
            return ACTOR

        app.dependency_overrides[get_current_user] = fake_actor
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(path)
        finally:
            app.dependency_overrides.clear()

    invalid_uuid = asyncio.run(execute("/v1/segments/not-a-uuid/vegetation-cover"))
    invalid_limit = asyncio.run(
        execute(f"/v1/segments/{SEGMENT_ID}/vegetation-cover?limit=101")
    )

    assert invalid_uuid.status_code == 422
    assert invalid_limit.status_code == 422
