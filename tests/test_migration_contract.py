import unittest
from pathlib import Path

MIGRATION = Path("infra/migrations/0001_source_catalog_and_staging.sql")
INVALID_POLYGON_MIGRATION = Path("infra/migrations/0002_allow_invalid_staging_polygons.sql")


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

if __name__ == "__main__":
    unittest.main()
