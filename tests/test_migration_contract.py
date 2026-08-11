import unittest
from pathlib import Path

MIGRATION = Path("infra/migrations/0001_source_catalog_and_staging.sql")
INVALID_POLYGON_MIGRATION = Path("infra/migrations/0002_allow_invalid_staging_polygons.sql")
SEGMENT_MIGRATION = Path("infra/migrations/0003_road_axis_candidates_and_segments.sql")
SATELLITE_MIGRATION = Path("infra/migrations/0004_satellite_analysis_foundation.sql")
SATELLITE_DISCOVERY_MIGRATION = Path("infra/migrations/0005_satellite_scene_discovery.sql")
SATELLITE_MULTIPOLYGON_MIGRATION = Path("infra/migrations/0006_satellite_scene_multipolygon.sql")
SATELLITE_VALIDATION_AOI = Path("scripts/prepare_satellite_validation_aoi.sql")
PARTIAL_CACHE_MIGRATION = Path("infra/migrations/0007_partial_satellite_cache.sql")
COMPOSE_FILE = Path("compose.yaml")
RECOMMENDATION_REVIEW_MIGRATION = Path("infra/migrations/0008_recommendation_review_audit.sql")
IDENTITY_REVIEW_POLICY_MIGRATION = Path("infra/migrations/0009_identity_and_review_policy.sql")
PREPARED_INSPECTION_ORDER_MIGRATION = Path("infra/migrations/0010_prepared_inspection_orders.sql")
PREPARED_MOBILE_SYNC_MIGRATION = Path("infra/migrations/0011_prepared_mobile_sync.sql")
PREPARED_DEMO_ORDER_EVENT_MIGRATION = Path("infra/migrations/0012_prepared_demo_order_events.sql")
PREPARED_PHOTO_MANIFEST_MIGRATION = Path("infra/migrations/0013_prepared_photo_manifest.sql")
DEMO_FINISH_PHOTO_MIGRATION = Path("infra/migrations/0014_require_demo_finish_photos.sql")
PHOTO_UPLOAD_RECEIPT_MIGRATION = Path("infra/migrations/0015_prepared_photo_upload_receipt.sql")
PHOTO_ACCESS_AUDIT_MIGRATION = Path("infra/migrations/0016_prepared_photo_access_audit.sql")


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

    def test_fresh_compose_database_applies_only_up_migrations_in_order(self) -> None:
        compose = COMPOSE_FILE.read_text(encoding="utf-8")

        mounts = [
            line.strip() for line in compose.splitlines() if "/docker-entrypoint-initdb.d/" in line
        ]
        self.assertEqual(len(mounts), 16)
        for version, mount in enumerate(mounts, start=1):
            prefix = f"{version:04d}"
            self.assertIn(f"infra/migrations/{prefix}_", mount)
            self.assertIn(f"/docker-entrypoint-initdb.d/{prefix}.sql:ro", mount)
            self.assertNotIn(".down.sql", mount)

    def test_recommendation_reviews_are_audited_and_append_only(self) -> None:
        sql = RECOMMENDATION_REVIEW_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE recommendation_review", sql)
        self.assertIn("vegetation_analysis_id uuid NOT NULL", sql)
        self.assertIn("idempotency_key char(64) NOT NULL UNIQUE", sql)
        self.assertIn("decision IN ('accepted', 'rejected', 'adjusted')", sql)
        self.assertIn("decision = 'accepted' OR btrim", sql)
        self.assertIn("reviewer_subject text NOT NULL", sql)
        self.assertIn("recommendation_review_chain_guard", sql)
        self.assertIn("recommendation_review_immutable", sql)
        self.assertIn("append-only", sql)

    def test_authenticated_review_policy_is_versioned_and_never_authorizes_work(self) -> None:
        sql = IDENTITY_REVIEW_POLICY_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE app_user", sql)
        self.assertIn("CREATE TABLE road_user_role", sql)
        self.assertIn("CREATE TABLE recommendation_review_policy", sql)
        self.assertIn("recommendation-review-mvp-v1", sql)
        self.assertIn("official_motiva_policy", sql)
        self.assertIn("CHECK (NOT authorizes_field_work)", sql)
        self.assertIn("recommendation_review_identity_policy_guard", sql)
        self.assertIn("recommendation review policies are immutable", sql)

    def test_prepared_inspection_orders_are_linked_non_operational_and_audited(self) -> None:
        sql = PREPARED_INSPECTION_ORDER_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE inspection_order_policy", sql)
        self.assertIn("CREATE TABLE work_order", sql)
        self.assertIn("source_review_id uuid NOT NULL UNIQUE", sql)
        self.assertIn("CREATE TABLE work_order_planned_point", sql)
        self.assertIn("cardinality(planned_point_fractions) = 3", sql)
        self.assertIn("CHECK (NOT authorizes_field_work)", sql)
        self.assertIn("CHECK (NOT eligible_for_field_execution)", sql)
        self.assertIn("prepared_inspection_order_guard", sql)
        self.assertIn("requires exactly three planned points", sql)
        self.assertIn("prepared inspection orders are immutable", sql)

    def test_mobile_sync_is_idempotent_append_only_and_non_operational(self) -> None:
        sql = PREPARED_MOBILE_SYNC_MIGRATION.read_text(encoding="utf-8")

        for table in (
            "mobile_device_registration",
            "mobile_device_revocation",
            "mobile_sync_batch",
            "mobile_sync_event",
            "mobile_sync_conflict",
            "prepared_field_measurement",
        ):
            self.assertIn(f"CREATE TABLE {table}", sql)
        self.assertIn("CREATE SEQUENCE mobile_sync_cursor_seq", sql)
        self.assertIn("batch_id uuid PRIMARY KEY", sql)
        self.assertIn("event_id uuid PRIMARY KEY", sql)
        self.assertIn("CHECK (NOT authorizes_field_work)", sql)
        self.assertIn("CHECK (NOT eligible_for_official_reporting)", sql)
        self.assertIn("prepared mobile sync records are append-only", sql)
        self.assertIn("prepared measurement requires its accepted sync event", sql)

    def test_demo_order_events_are_simulated_sequenced_and_non_operational(self) -> None:
        sql = PREPARED_DEMO_ORDER_EVENT_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE prepared_work_order_demo_event", sql)
        self.assertIn("operation IN ('confirm', 'start', 'finish')", sql)
        self.assertIn("simulation_scope = 'demo_only'", sql)
        self.assertIn("data_status = 'simulated'", sql)
        self.assertIn("CHECK (NOT authorizes_field_work)", sql)
        self.assertIn("start requires a persisted confirm event", sql)
        self.assertIn("finish requires start and three prepared point measurements", sql)
        self.assertIn("prepared_work_order_demo_event_immutable", sql)

    def test_photo_manifest_is_unuploaded_unvalidated_and_append_only(self) -> None:
        sql = PREPARED_PHOTO_MANIFEST_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE prepared_field_photo_manifest", sql)
        self.assertIn("checksum_sha256 ~ '^[0-9a-f]{64}$'", sql)
        self.assertIn("content_status = 'not_uploaded'", sql)
        self.assertIn("ruler_status = 'not_validated'", sql)
        self.assertIn("quality_status = 'prepared_unverified'", sql)
        self.assertIn("CHECK (NOT authorizes_field_work)", sql)
        self.assertIn("CHECK (NOT eligible_for_official_reporting)", sql)
        self.assertIn("prepared photo manifest requires its exact accepted sync event", sql)
        self.assertIn("prepared_field_photo_manifest_immutable", sql)

    def test_demo_finish_requires_three_distinct_photo_manifests(self) -> None:
        sql = DEMO_FINISH_PHOTO_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("count(DISTINCT photo.planned_point_id)", sql)
        self.assertIn("finish requires three prepared point photo manifests", sql)
        self.assertIn("prepared_demo_finish_photo_guard", sql)

    def test_photo_upload_receipt_is_encrypted_versioned_and_append_only(self) -> None:
        sql = PHOTO_UPLOAD_RECEIPT_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE prepared_photo_upload_receipt", sql)
        self.assertIn("object_version_id text NOT NULL", sql)
        self.assertIn("encryption_method = 'APP-AES256-GCM'", sql)
        self.assertIn("content_status = 'uploaded_unverified'", sql)
        self.assertIn("photo upload receipt requires its exact prepared manifest", sql)
        self.assertIn("prepared_photo_upload_receipt_immutable", sql)

    def test_prepared_photo_access_is_authorized_exact_and_append_only(self) -> None:
        sql = PHOTO_ACCESS_AUDIT_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE prepared_photo_access_event", sql)
        self.assertIn("access_purpose = 'human_review'", sql)
        self.assertIn("assignment.role IN ('manager', 'supervisor')", sql)
        self.assertIn("receipt.checksum_sha256 = NEW.checksum_sha256", sql)
        self.assertIn("CHECK (NOT eligible_for_official_reporting)", sql)
        self.assertIn("prepared_photo_access_event_immutable", sql)


if __name__ == "__main__":
    unittest.main()
