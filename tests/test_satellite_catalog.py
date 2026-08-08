import unittest
from datetime import UTC, datetime

from zenit_geospatial.satellite_catalog import catalog_checksum, catalog_metadata
from zenit_geospatial.satellite_providers import Acquisition


def acquisition() -> Acquisition:
    return Acquisition(
        provider="copernicus_sentinel_hub",
        collection="sentinel-2-l2a",
        sensor="sentinel-2",
        external_scene_id="scene-1",
        acquired_at=datetime(2026, 8, 5, 13, 10, tzinfo=UTC),
        bbox=(-46.8, -23.55, -46.76, -23.5),
        geometry={"type": "Polygon", "coordinates": []},
        cloud_cover_percent=12.5,
        assets={},
        source_metadata={"datetime": "2026-08-05T13:10:00Z", "eo:cloud_cover": 12.5},
    )


class SatelliteCatalogTests(unittest.TestCase):
    def test_catalog_checksum_is_deterministic_and_sensitive_to_provenance(self) -> None:
        scene = acquisition()

        self.assertEqual(catalog_checksum(scene), catalog_checksum(scene))
        self.assertEqual(len(catalog_checksum(scene)), 64)

        changed = Acquisition(
            provider=scene.provider,
            collection=scene.collection,
            sensor=scene.sensor,
            external_scene_id=scene.external_scene_id,
            acquired_at=scene.acquired_at,
            bbox=scene.bbox,
            geometry=scene.geometry,
            cloud_cover_percent=99,
            assets=scene.assets,
            source_metadata=scene.source_metadata,
        )
        self.assertNotEqual(catalog_checksum(scene), catalog_checksum(changed))

    def test_catalog_metadata_explicitly_marks_catalog_only(self) -> None:
        metadata = catalog_metadata(acquisition())

        self.assertIs(metadata["catalog_only"], True)
        self.assertEqual(metadata["assets"], {})


if __name__ == "__main__":
    unittest.main()
