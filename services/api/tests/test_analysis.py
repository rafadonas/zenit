import asyncio

from httpx import ASGITransport, AsyncClient

from zenit_api.analysis import AnalysisPreviewRequest, calculate_ndvi, evaluate_analysis
from zenit_api.main import app


def test_calculates_ndvi() -> None:
    assert calculate_ndvi(0.2, 0.6) == 0.5
    assert calculate_ndvi(0, 0) is None


def test_low_quality_scene_requires_inspection() -> None:
    result = evaluate_analysis(
        AnalysisPreviewRequest(
            zone_type="left",
            red_reflectance=0.2,
            nir_reflectance=0.6,
            valid_pixel_percent=40,
            scene_quality="low",
            scene_data_status="real",
        )
    )

    assert result.conclusion == "inconclusive"
    assert result.recommendation == "inspect"
    assert result.confidence_band == "low"
    assert not result.eligible_for_official_reporting


def test_ndvi_alone_never_infers_height() -> None:
    result = evaluate_analysis(
        AnalysisPreviewRequest(
            zone_type="left",
            red_reflectance=0.1,
            nir_reflectance=0.8,
            valid_pixel_percent=95,
            scene_quality="acceptable",
            scene_data_status="real",
        )
    )

    assert result.recommendation == "inspect"
    assert "does not measure vegetation height" in result.reasons[0]


def test_special_zone_uses_ten_centimeter_threshold_and_human_review() -> None:
    result = evaluate_analysis(
        AnalysisPreviewRequest(
            zone_type="special",
            red_reflectance=0.2,
            nir_reflectance=0.6,
            valid_pixel_percent=90,
            scene_quality="acceptable",
            scene_data_status="real",
            observed_height_cm=12,
            height_data_status="real",
        )
    )

    assert result.threshold_cm == 10
    assert result.recommendation == "mowing_review"
    assert result.requires_human_approval


def test_preview_endpoint_marks_prepared_scene_inconclusive() -> None:
    async def post_preview():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/v1/analysis/preview",
                json={
                    "zone_type": "median",
                    "red_reflectance": 0.2,
                    "nir_reflectance": 0.6,
                    "valid_pixel_percent": 90,
                    "scene_quality": "acceptable",
                    "scene_data_status": "prepared",
                },
            )

    response = asyncio.run(post_preview())

    assert response.status_code == 200
    assert response.json()["recommendation"] == "inspect"
