BEGIN;

CREATE TABLE road (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text NOT NULL UNIQUE,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE road_axis_candidate (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    road_id uuid NOT NULL REFERENCES road(id),
    source_import_run_id uuid NOT NULL REFERENCES import_run(id),
    version integer NOT NULL CHECK (version > 0),
    derivation_method text NOT NULL,
    validation_status text NOT NULL DEFAULT 'needs_validation'
        CHECK (validation_status IN ('needs_validation', 'validated', 'rejected')),
    data_status text NOT NULL DEFAULT 'estimated'
        CHECK (data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')),
    eligible_for_operations boolean NOT NULL DEFAULT false,
    source_geometry geometry(LineString, 4326) NOT NULL,
    metric_geometry geometry(LineString, 31983) NOT NULL,
    length_m double precision NOT NULL CHECK (length_m > 0),
    quality_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (road_id, source_import_run_id, version),
    CHECK (ST_IsValid(source_geometry)),
    CHECK (ST_IsValid(metric_geometry)),
    CHECK (abs(ST_Length(metric_geometry) - length_m) < 0.01),
    CHECK (validation_status = 'validated' OR NOT eligible_for_operations)
);

CREATE INDEX road_axis_candidate_source_gix
    ON road_axis_candidate USING gist (source_geometry);
CREATE INDEX road_axis_candidate_metric_gix
    ON road_axis_candidate USING gist (metric_geometry);

CREATE TABLE road_segment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    road_axis_candidate_id uuid NOT NULL REFERENCES road_axis_candidate(id) ON DELETE CASCADE,
    segment_index integer NOT NULL CHECK (segment_index >= 0),
    start_distance_m double precision NOT NULL CHECK (start_distance_m >= 0),
    end_distance_m double precision NOT NULL CHECK (end_distance_m > start_distance_m),
    metric_geometry geometry(LineString, 31983) NOT NULL,
    data_status text NOT NULL DEFAULT 'estimated'
        CHECK (data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')),
    eligible_for_operations boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (road_axis_candidate_id, segment_index),
    CHECK (ST_IsValid(metric_geometry)),
    CHECK (abs(ST_Length(metric_geometry) - (end_distance_m - start_distance_m)) < 0.10)
);

CREATE INDEX road_segment_geometry_gix ON road_segment USING gist (metric_geometry);
CREATE INDEX road_segment_distance_idx
    ON road_segment (road_axis_candidate_id, start_distance_m, end_distance_m);

COMMIT;
