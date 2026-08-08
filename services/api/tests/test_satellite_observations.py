import asyncio
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from zenit_api.main import app
from zenit_api.satellite_observations import (
    SatelliteAssetEvidence,
    SatelliteObservation,
    SatelliteObservationCollection,
    get_satellite_observation_reader,
)

SEGMENT_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakeReader:
    async def by_segment(
        self, segment_id: UUID, *, limit: int
    ) -> SatelliteObservationCollection:
        assert segment_id == SEGMENT_ID
        assert limit == 10
        return SatelliteObservationCollection(
            items=[
                SatelliteObservation(
                    analysis_run_id=UUID("00000000-0000-0000-0000-000000000002"),
                    scene_id=UUID("00000000-0000-0000-0000-000000000003"),
                    provider="copernicus_sentinel_hub",
                    collection="sentinel-2-l2a",
                    sensor="sentinel-2",
                    acquired_at="2026-07-29T13:00:00+00:00",
                    cache_status="partially_cached",
                    scene_data_status="real",
                    zone_type="left",
                    zone_data_status="prepared",
                    mean_ndvi=0.097354,
                    valid_pixel_percent=100,
                    conclusion="inconclusive",
                    recommendation="inspect",
                    confidence_band="low",
                    requires_human_approval=True,
                    eligible_for_official_reporting=False,
                    rule_version="satellite-quality-2026-08-07.1",
                    processor_version="sentinel-ndvi-scl-v1",
                    explanation={"input_data_status": "prepared"},
                    assets=[
                        SatelliteAssetEvidence(
                            role="ndvi_aoi_crop_fixture",
                            media_type="image/tiff",
                            checksum_sha256="a" * 64,
                        )
                    ],
                )
            ],
            metadata={"segment_id": str(segment_id), "result_count": 1},
        )


def test_endpoint_exposes_safety_labels_and_checksums_without_storage_uri() -> None:
    async def fake_reader() -> FakeReader:
        return FakeReader()

    async def request():
        app.dependency_overrides[get_satellite_observation_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(
                    f"/v1/segments/{SEGMENT_ID}/satellite-observations?limit=10"
                )
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["conclusion"] == "inconclusive"
    assert payload["items"][0]["recommendation"] == "inspect"
    assert payload["items"][0]["eligible_for_official_reporting"] is False
    assert payload["items"][0]["assets"][0]["checksum_sha256"] == "a" * 64
    assert "storage_uri" not in payload["items"][0]["assets"][0]


def test_endpoint_rejects_invalid_uuid_and_limit() -> None:
    async def request(path: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    invalid_uuid = asyncio.run(request("/v1/segments/not-a-uuid/satellite-observations"))
    invalid_limit = asyncio.run(
        request(f"/v1/segments/{SEGMENT_ID}/satellite-observations?limit=101")
    )

    assert invalid_uuid.status_code == 422
    assert invalid_limit.status_code == 422
