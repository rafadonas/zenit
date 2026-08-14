import asyncio

from httpx import ASGITransport, AsyncClient

from zenit_api.main import app
from zenit_api.segments import (
    BoundingBox,
    LineStringGeometry,
    SegmentFeature,
    SegmentFeatureCollection,
    SegmentProperties,
    get_segment_reader,
)


class FakeSegmentReader:
    async def by_bbox(self, road_code: str, bbox: BoundingBox) -> SegmentFeatureCollection:
        assert road_code == "SP021"
        assert bbox.min_longitude == -46.84
        return SegmentFeatureCollection(
            features=[
                SegmentFeature(
                    geometry=LineStringGeometry(coordinates=[[-46.83, -23.63], [-46.829, -23.629]]),
                    properties=SegmentProperties(
                        segment_id="segment-1",
                        segment_index=0,
                        start_distance_m=0,
                        end_distance_m=100,
                        data_status="estimated",
                        validation_status="needs_validation",
                        eligible_for_operations=False,
                    ),
                )
            ],
            metadata={"road_code": road_code},
        )


async def get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def fake_segment_reader() -> FakeSegmentReader:
    return FakeSegmentReader()


def test_segments_returns_geojson_with_provenance_labels() -> None:
    app.dependency_overrides[get_segment_reader] = fake_segment_reader
    try:
        response = asyncio.run(
            get(
                "/v1/roads/SP021/segments"
                "?min_lon=-46.84&min_lat=-23.64&max_lon=-46.72&max_lat=-23.40"
            )
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert payload["features"][0]["properties"]["data_status"] == "estimated"
    assert payload["features"][0]["properties"]["eligible_for_operations"] is False


def test_segments_rejects_inverted_bbox_before_repository_call() -> None:
    app.dependency_overrides[get_segment_reader] = fake_segment_reader
    try:
        response = asyncio.run(
            get(
                "/v1/roads/SP021/segments"
                "?min_lon=-46.72&min_lat=-23.40&max_lon=-46.84&max_lat=-23.64"
            )
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "unprocessable_content"
    assert payload["message"] == "Bounding box minimums must be below maximums"
    assert payload["correlation_id"] == response.headers["x-correlation-id"]
