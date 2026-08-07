BEGIN;

CREATE TABLE segment_zone (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    road_segment_id uuid NOT NULL REFERENCES road_segment(id) ON DELETE CASCADE,
    zone_type text NOT NULL CHECK (zone_type IN ('left', 'right', 'median', 'special')),
    metric_geometry geometry(Polygon, 31983),
    threshold_cm numeric(6, 2) NOT NULL CHECK (threshold_cm > 0),
    data_status text NOT NULL DEFAULT 'prepared'
        CHECK (data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')),
    eligible_for_operations boolean NOT NULL DEFAULT false,
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (road_segment_id, zone_type),
    CHECK (metric_geometry IS NULL OR ST_IsValid(metric_geometry)),
    CHECK (zone_type = 'special' OR threshold_cm = 30.00),
    CHECK (zone_type <> 'special' OR threshold_cm = 10.00),
    CHECK (data_status = 'real' OR NOT eligible_for_operations)
);

CREATE INDEX segment_zone_geometry_gix ON segment_zone USING gist (metric_geometry);

CREATE TABLE satellite_scene (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    external_scene_id text NOT NULL,
    sensor text NOT NULL CHECK (sensor IN ('sentinel-2', 'cbers-4a')),
    acquired_at timestamptz NOT NULL,
    cached_at timestamptz NOT NULL,
    footprint geometry(Polygon, 4326),
    cloud_cover_percent numeric(5, 2)
        CHECK (cloud_cover_percent BETWEEN 0 AND 100),
    quality_status text NOT NULL DEFAULT 'pending'
        CHECK (quality_status IN ('pending', 'acceptable', 'low', 'rejected')),
    data_status text NOT NULL DEFAULT 'prepared'
        CHECK (data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, external_scene_id),
    CHECK (footprint IS NULL OR ST_IsValid(footprint))
);

CREATE TABLE satellite_asset (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    satellite_scene_id uuid NOT NULL REFERENCES satellite_scene(id) ON DELETE CASCADE,
    asset_role text NOT NULL,
    storage_uri text NOT NULL,
    checksum_sha256 char(64) NOT NULL,
    media_type text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (satellite_scene_id, asset_role, checksum_sha256)
);

CREATE TABLE analysis_run (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    satellite_scene_id uuid NOT NULL REFERENCES satellite_scene(id),
    rule_version text NOT NULL,
    processor_version text NOT NULL,
    idempotency_key char(64) NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed')),
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CHECK ((status = 'completed') = (completed_at IS NOT NULL))
);

CREATE TABLE vegetation_analysis (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_run_id uuid NOT NULL REFERENCES analysis_run(id) ON DELETE CASCADE,
    segment_zone_id uuid NOT NULL REFERENCES segment_zone(id),
    mean_ndvi numeric(7, 6) CHECK (mean_ndvi BETWEEN -1 AND 1),
    valid_pixel_percent numeric(5, 2) NOT NULL
        CHECK (valid_pixel_percent BETWEEN 0 AND 100),
    observed_height_cm numeric(8, 2) CHECK (observed_height_cm >= 0),
    height_data_status text
        CHECK (height_data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')),
    conclusion text NOT NULL CHECK (conclusion IN ('conclusive', 'inconclusive')),
    recommendation text NOT NULL CHECK (recommendation IN ('monitor', 'inspect', 'mowing_review')),
    confidence_band text NOT NULL CHECK (confidence_band IN ('low', 'medium', 'high')),
    explanation jsonb NOT NULL,
    requires_human_approval boolean NOT NULL DEFAULT true,
    eligible_for_official_reporting boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (analysis_run_id, segment_zone_id),
    CHECK (observed_height_cm IS NOT NULL OR height_data_status IS NULL),
    CHECK (recommendation <> 'mowing_review' OR requires_human_approval),
    CHECK (height_data_status = 'real' OR NOT eligible_for_official_reporting)
);

COMMIT;
