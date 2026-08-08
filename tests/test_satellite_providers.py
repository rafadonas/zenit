import unittest
from datetime import UTC, datetime

from zenit_geospatial.satellite_providers import (
    CBERS_WFI_COLLECTION,
    BoundingBox,
    CbersStacProvider,
    ProviderResponseError,
    SearchWindow,
    SentinelCatalogProvider,
)


class SatelliteProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bbox = BoundingBox(-46.80, -23.55, -46.76, -23.50)
        self.window = SearchWindow(
            datetime(2026, 8, 1, tzinfo=UTC),
            datetime(2026, 8, 7, tzinfo=UTC),
        )

    def test_sentinel_request_preserves_100m_aoi_bbox_and_utc_window(self) -> None:
        request = SentinelCatalogProvider().build_search_request(self.bbox, self.window, limit=20)

        self.assertEqual(request["collections"], ["sentinel-2-l2a"])
        self.assertEqual(request["bbox"], [-46.80, -23.55, -46.76, -23.50])
        self.assertEqual(request["datetime"], "2026-08-01T00:00:00Z/2026-08-07T00:00:00Z")

    def test_sentinel_page_keeps_scene_quality_metadata_and_pagination(self) -> None:
        page = SentinelCatalogProvider().parse_search_page(
            {
                "features": [
                    {
                        "id": "S2-scene-1",
                        "collection": "sentinel-2-l2a",
                        "bbox": [-46.8, -23.55, -46.76, -23.5],
                        "geometry": {"type": "Polygon", "coordinates": []},
                        "properties": {
                            "datetime": "2026-08-05T13:10:00Z",
                            "eo:cloud_cover": 12.5,
                        },
                    }
                ],
                "links": [{"rel": "next", "href": "https://provider.invalid/next"}],
                "context": {"next": 5},
            }
        )

        acquisition = page.acquisitions[0]
        self.assertEqual(acquisition.external_scene_id, "S2-scene-1")
        self.assertEqual(acquisition.cloud_cover_percent, 12.5)
        self.assertEqual(acquisition.assets, {})
        self.assertEqual(page.next_url, "https://provider.invalid/next")
        self.assertEqual(page.next_token, 5)

    def test_cbers_page_preserves_collection_and_asset_hrefs(self) -> None:
        provider = CbersStacProvider(CBERS_WFI_COLLECTION)
        page = provider.parse_search_page(
            {
                "features": [
                    {
                        "id": "CBERS-scene-1",
                        "collection": CBERS_WFI_COLLECTION,
                        "properties": {"datetime": "2026-08-05T13:10:00Z"},
                        "assets": {
                            "BAND15": {"href": "https://provider.invalid/red.tif"},
                            "BAND16": {"href": "https://provider.invalid/nir.tif"},
                            "missing": {"type": "image/tiff"},
                        },
                    }
                ]
            }
        )

        acquisition = page.acquisitions[0]
        self.assertEqual(acquisition.sensor, "cbers-4a")
        self.assertEqual(acquisition.collection, CBERS_WFI_COLLECTION)
        self.assertEqual(
            acquisition.assets,
            {
                "BAND15": "https://provider.invalid/red.tif",
                "BAND16": "https://provider.invalid/nir.tif",
            },
        )

    def test_invalid_or_ambiguous_provider_payload_fails_closed(self) -> None:
        with self.assertRaisesRegex(ProviderResponseError, "features array"):
            SentinelCatalogProvider().parse_search_page({})
        with self.assertRaisesRegex(ProviderResponseError, "acquisition datetime"):
            SentinelCatalogProvider().parse_search_page(
                {"features": [{"id": "scene-without-time", "properties": {}}]}
            )

    def test_search_window_requires_timezone_and_order(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            SearchWindow(datetime(2026, 8, 1), datetime(2026, 8, 2))
        with self.assertRaisesRegex(ValueError, "start must be before end"):
            SearchWindow(
                datetime(2026, 8, 2, tzinfo=UTC),
                datetime(2026, 8, 1, tzinfo=UTC),
            )


if __name__ == "__main__":
    unittest.main()
