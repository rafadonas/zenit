import pytest
from scripts.render_cached_ndvi_preview import (
    EXPECTED_METADATA_SHA256,
    EXPECTED_TIFF_SHA256,
    PROCESSOR_VERSION,
    SOURCE_METADATA,
    SOURCE_TIFF,
    render,
)

pytestmark = pytest.mark.skipif(
    not SOURCE_TIFF.exists() or not SOURCE_METADATA.exists(),
    reason="ignored checksummed satellite cache is not available",
)


def test_cached_ndvi_preview_preserves_provenance_and_safety_labels() -> None:
    report, lineage = render()

    assert "Prévia do recorte Sentinel-2 com filtro NDVI" in report
    assert "não mede altura" in report
    assert "não autoriza trabalho de campo" in report
    assert "não uma composição RGB/foto normal" in report
    assert lineage["processor_version"] == PROCESSOR_VERSION
    assert lineage["source"]["sha256"] == EXPECTED_TIFF_SHA256
    assert lineage["source"]["metadata_sha256"] == EXPECTED_METADATA_SHA256
    assert lineage["spatial_scope_status"] == "prepared_estimated_aoi"
    assert lineage["result_status"] == "inconclusive"
    assert lineage["operational_eligibility"] is False
    assert lineage["eligible_for_model_training"] is False
    assert lineage["eligible_for_official_reporting"] is False


def test_cached_ndvi_preview_reads_the_expected_float_grid() -> None:
    _, lineage = render()
    statistics = lineage["statistics"]

    assert statistics["width"] == 5
    assert statistics["height"] == 11
    assert statistics["valid_pixels"] == 35
    assert statistics["nodata_pixels"] == 20
    assert statistics["minimum_ndvi"] == -0.15737704932689667
    assert statistics["maximum_ndvi"] == 0.28398269414901733
    assert statistics["mean_ndvi_cached_geotiff"] == 0.07995302099734544
    assert lineage["bounds_epsg_4326"] == {
        "west": -46.818348331098555,
        "south": -23.54129614537441,
        "east": -46.81789266067068,
        "north": -23.540378237276762,
    }
