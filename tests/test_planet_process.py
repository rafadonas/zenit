from uuid import UUID

import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from zenit_geospatial.planet_process import (
    PROCESSOR_VERSION,
    ProcessingError,
    explanation,
    geometry_hash,
    idempotency_key,
    summarize,
    zone_statistics,
)
from zenit_geospatial.sentinel_statistics import QualityStatus

ZONE_ID = UUID("48000000-0000-4000-8000-000000000001")
SCENE_ID = UUID("48000000-0000-4000-8000-000000000002")
ORIGIN_X, ORIGIN_Y, PIXEL = 300000.0, 7390000.0, 3.0
SRID = 31983


def raster(bands: np.ndarray, dtype: str) -> bytes:
    count, height, width = bands.shape
    profile = {
        "driver": "GTiff",
        "count": count,
        "height": height,
        "width": width,
        "dtype": dtype,
        "crs": rasterio.crs.CRS.from_epsg(SRID),
        "transform": from_origin(ORIGIN_X, ORIGIN_Y, PIXEL, PIXEL),
    }
    with MemoryFile() as memory:
        with memory.open(**profile) as dataset:
            dataset.write(bands)
        return memory.read()


def analytic(red: float = 1000.0, nir: float = 3000.0, shape=(4, 4)) -> bytes:
    blue = np.full(shape, 500.0, dtype="float32")
    green = np.full(shape, 700.0, dtype="float32")
    red_band = np.full(shape, red, dtype="float32")
    nir_band = np.full(shape, nir, dtype="float32")
    return raster(np.stack([blue, green, red_band, nir_band]), "float32")


def udm2(clear: np.ndarray | None = None, shape=(4, 4)) -> bytes:
    mask = np.ones(shape, dtype="uint8") if clear is None else clear.astype("uint8")
    return raster(np.stack([mask]), "uint8")


def full_zone() -> dict:
    x0, y0 = ORIGIN_X, ORIGIN_Y
    x1, y1 = ORIGIN_X + 4 * PIXEL, ORIGIN_Y - 4 * PIXEL
    return {
        "type": "Polygon",
        "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
    }


def test_ndvi_matches_the_reflectance_definition() -> None:
    result = zone_statistics(
        segment_zone_id=ZONE_ID, analytic=analytic(), udm2=udm2(), geometry=full_zone()
    )

    # (3000 - 1000) / (3000 + 1000)
    assert result.mean_ndvi == pytest.approx(0.5)
    assert result.min_ndvi == result.max_ndvi == pytest.approx(0.5)
    assert result.valid_pixels == result.total_pixels == 16
    assert result.valid_pixel_percent == 100.0
    assert result.quality_status == QualityStatus.ACCEPTED


def test_udm2_masks_cloud_and_shadow_pixels_before_the_statistic() -> None:
    clear = np.ones((4, 4), dtype="uint8")
    clear[:2, :] = 0  # half of the zone is cloud, shadow or otherwise not clear

    result = zone_statistics(
        segment_zone_id=ZONE_ID, analytic=analytic(), udm2=udm2(clear), geometry=full_zone()
    )

    assert result.valid_pixels == 8
    assert result.valid_pixel_percent == 50.0
    assert result.quality_status == QualityStatus.WARNING
    assert result.mean_ndvi == pytest.approx(0.5)


def test_zone_without_usable_pixels_reports_no_observation() -> None:
    result = zone_statistics(
        segment_zone_id=ZONE_ID,
        analytic=analytic(),
        udm2=udm2(np.zeros((4, 4), dtype="uint8")),
        geometry=full_zone(),
    )

    assert result.valid_pixels == 0
    assert result.mean_ndvi is None
    assert result.quality_status == QualityStatus.NO_OBSERVATION


def test_zero_reflectance_pixels_never_divide_by_zero() -> None:
    result = zone_statistics(
        segment_zone_id=ZONE_ID,
        analytic=analytic(red=0.0, nir=0.0),
        udm2=udm2(),
        geometry=full_zone(),
    )

    assert result.valid_pixels == 0
    assert result.quality_status == QualityStatus.NO_OBSERVATION


def test_geometry_outside_the_raster_is_refused() -> None:
    far_away = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
    }

    with pytest.raises(ProcessingError, match="does not overlap"):
        zone_statistics(
            segment_zone_id=ZONE_ID, analytic=analytic(), udm2=udm2(), geometry=far_away
        )


def test_mismatched_grids_are_refused() -> None:
    with pytest.raises(ProcessingError, match="same grid"):
        zone_statistics(
            segment_zone_id=ZONE_ID,
            analytic=analytic(),
            udm2=udm2(shape=(2, 2)),
            geometry=full_zone(),
        )


def test_analytic_without_nir_is_refused() -> None:
    three_bands = np.stack([np.full((4, 4), 1.0, dtype="float32")] * 3)

    with pytest.raises(ProcessingError, match="NIR band"):
        zone_statistics(
            segment_zone_id=ZONE_ID,
            analytic=raster(three_bands, "float32"),
            udm2=udm2(),
            geometry=full_zone(),
        )


def test_idempotency_key_is_stable_and_input_sensitive() -> None:
    base = {
        "scene_id": SCENE_ID,
        "segment_zone_id": ZONE_ID,
        "analytic_checksum": "a" * 64,
        "udm2_checksum": "b" * 64,
        "geometry_hash": "c" * 64,
    }

    assert idempotency_key(**base) == idempotency_key(**base)
    assert idempotency_key(**{**base, "analytic_checksum": "d" * 64}) != idempotency_key(**base)
    assert idempotency_key(**{**base, "geometry_hash": "d" * 64}) != idempotency_key(**base)


def test_geometry_hash_ignores_key_order() -> None:
    first = geometry_hash({"type": "Polygon", "coordinates": [[[0, 0]]]})
    second = geometry_hash({"coordinates": [[[0, 0]]], "type": "Polygon"})

    assert first == second


def test_explanation_never_claims_height_or_authorization() -> None:
    result = zone_statistics(
        segment_zone_id=ZONE_ID, analytic=analytic(), udm2=udm2(), geometry=full_zone()
    )

    payload = explanation(
        result,
        analytic_checksum="a" * 64,
        udm2_checksum="b" * 64,
        geometry_hash_value="c" * 64,
        zone_data_status="prepared",
    )

    assert payload["result_data_status"] == "inconclusive"
    assert payload["offline"] is True
    assert payload["processor_version"] == PROCESSOR_VERSION
    assert "height" not in {key.lower() for key in payload}
    assert any("never a vegetation height" in reason for reason in payload["reasons"])


def test_summary_counts_zones_and_denies_operational_use() -> None:
    accepted = zone_statistics(
        segment_zone_id=ZONE_ID, analytic=analytic(), udm2=udm2(), geometry=full_zone()
    )
    empty = zone_statistics(
        segment_zone_id=ZONE_ID,
        analytic=analytic(),
        udm2=udm2(np.zeros((4, 4), dtype="uint8")),
        geometry=full_zone(),
    )

    report = summarize([accepted, empty])

    assert report["zones"] == 2
    assert report["zones_by_quality"] == {"accepted": 1, "no_observation": 1}
    assert report["provider_calls"] == 0
    assert report["conclusion"] == "inconclusive"
    assert report["eligible_for_operations"] is False
    assert report["eligible_for_official_reporting"] is False
