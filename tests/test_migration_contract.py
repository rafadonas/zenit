import unittest
from pathlib import Path

MIGRATION = Path("infra/migrations/0001_source_catalog_and_staging.sql")
INVALID_POLYGON_MIGRATION = Path("infra/migrations/0002_allow_invalid_staging_polygons.sql")
SEGMENT_MIGRATION = Path("infra/migrations/0003_road_axis_candidates_and_segments.sql")
SATELLITE_MIGRATION = Path("infra/migrations/0004_satellite_analysis_foundation.sql")
SATELLITE_DISCOVERY_MIGRATION = Path("infra/migrations/0005_satellite_scene_discovery.sql")
SATELLITE_MULTIPOLYGON_MIGRATION = Path(
    "infra/migrations/0006_satellite_scene_multipolygon.sql"
)
SATELLITE_VALIDATION_AOI = Path("scripts/prepare_satellite_validation_aoi.sql")
PARTIAL_CACHE_MIGRATION = Path("infra/migrations/0007_partial_satellite_cache.sql")


class MigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")

    def test_enables_postgis_and_uses_explicit_source_srid(self) -> None:
        self.assertIn("CREATE EXTENSION IF NOT EXISTS postgis", self.sql)
        self.assertIn("geometry(Point, 4326)", self.sql)
        self.assertIn("geometry(Polygon, 4326)", self.sql)

    def test_keeps_source_import_staging_and_lineage_separate(self) -> None:
        for table in (
            "source_file",
            "import_job",
            "import_run",
            "import_anomaly",
            "staging_km_marker",
            "staging_mowing_polygon",
            "staging_vegetation_observation",
            "data_lineage",
        ):
            self.assertIn(f"CREATE TABLE {table}", self.sql)

    def test_idempotency_and_inference_status_are_constrained(self) -> None:
        self.assertIn("idempotency_key char(64) NOT NULL UNIQUE", self.sql)
        self.assertIn("UNIQUE (import_job_id, attempt_number)", self.sql)
        self.assertIn("inference_status text NOT NULL DEFAULT 'needs_validation'", self.sql)
        self.assertIn("vegetation_class IN ('N1', 'N2', 'N3', 'X')", self.sql)

    def test_followup_migration_preserves_invalid_source_polygon_evidence(self) -> None:
        sql = INVALID_POLYGON_MIGRATION.read_text(encoding="utf-8")

        self.assertIn(
            "DROP CONSTRAINT staging_mowing_polygon_original_geometry_check",
            sql,
        )

    def test_segment_schema_uses_metric_crs_and_blocks_unvalidated_axis(self) -> None:
        sql = SEGMENT_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("geometry(LineString, 31983)", sql)
        self.assertIn("validation_status = 'validated' OR NOT eligible_for_operations", sql)
        self.assertIn("UNIQUE (road_axis_candidate_id, segment_index)", sql)

    def test_satellite_analysis_preserves_quality_provenance_and_human_approval(self) -> None:
        sql = SATELLITE_MIGRATION.read_text(encoding="utf-8")

        for table in (
            "segment_zone",
            "satellite_scene",
            "satellite_asset",
            "analysis_run",
            "vegetation_analysis",
        ):
            self.assertIn(f"CREATE TABLE {table}", sql)
        self.assertIn("idempotency_key char(64) NOT NULL UNIQUE", sql)
        self.assertIn("checksum_sha256 char(64) NOT NULL", sql)
        self.assertIn("recommendation <> 'mowing_review' OR requires_human_approval", sql)
        self.assertIn("zone_type = 'special' OR threshold_cm = 30.00", sql)
        self.assertIn("zone_type <> 'special' OR threshold_cm = 10.00", sql)

    def test_satellite_discovery_is_distinct_from_cached_raster(self) -> None:
        sql = SATELLITE_DISCOVERY_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("ALTER COLUMN cached_at DROP NOT NULL", sql)
        self.assertIn("ADD COLUMN discovered_at timestamptz NOT NULL", sql)
        self.assertIn("ADD COLUMN collection text", sql)
        self.assertIn("ADD COLUMN catalog_checksum_sha256 char(64)", sql)
        self.assertIn("cache_status IN ('discovered', 'cached')", sql)
        self.assertIn("(cache_status = 'cached') = (cached_at IS NOT NULL)", sql)

    def test_satellite_scene_preserves_multipart_provider_footprints(self) -> None:
        sql = SATELLITE_MULTIPOLYGON_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("geometry(MultiPolygon, 4326)", sql)
        self.assertIn("USING ST_Multi(footprint)", sql)

    def test_satellite_validation_aoi_is_prepared_and_non_operational(self) -> None:
        sql = SATELLITE_VALIDATION_AOI.read_text(encoding="utf-8")

        self.assertIn("segment.segment_index = 195", sql)
        self.assertIn("('left', 30.00::numeric, 'left')", sql)
        self.assertIn("('right', 30.00::numeric, 'right')", sql)
        self.assertIn("('special', 10.00::numeric, NULL)", sql)
        self.assertIn("'prepared'", sql)
        self.assertIn("'buffer_width_is_official', false", sql)
        self.assertIn("'eligible_for_official_reporting', false", sql)

    def test_partial_cache_does_not_claim_full_scene_cache(self) -> None:
        sql = PARTIAL_CACHE_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("'partially_cached'", sql)
        self.assertIn("(cache_status = 'discovered') = (cached_at IS NULL)", sql)


if __name__ == "__main__":
    unittest.main()
