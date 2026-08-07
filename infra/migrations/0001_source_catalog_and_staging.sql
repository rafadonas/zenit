BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE source_file (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sha256 char(64) NOT NULL UNIQUE,
    original_path text NOT NULL,
    original_name text NOT NULL,
    size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
    detected_format text NOT NULL,
    storage_uri text NOT NULL,
    data_status text NOT NULL DEFAULT 'real'
        CHECK (data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')),
    reference_date date,
    received_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE import_job (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_file_id uuid NOT NULL REFERENCES source_file(id),
    parser_name text NOT NULL,
    parser_version text NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key char(64) NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    UNIQUE (source_file_id, parser_name, parser_version, parameters)
);

CREATE INDEX import_job_source_file_idx ON import_job (source_file_id);

CREATE TABLE import_run (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    import_job_id uuid NOT NULL REFERENCES import_job(id),
    attempt_number integer NOT NULL CHECK (attempt_number > 0),
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'rejected')),
    record_count integer CHECK (record_count IS NULL OR record_count >= 0),
    warning_count integer NOT NULL DEFAULT 0 CHECK (warning_count >= 0),
    error_count integer NOT NULL DEFAULT 0 CHECK (error_count >= 0),
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (finished_at IS NULL OR started_at IS NOT NULL),
    UNIQUE (import_job_id, attempt_number)
);

CREATE INDEX import_run_job_idx ON import_run (import_job_id);
CREATE INDEX import_run_status_idx ON import_run (status);

CREATE TABLE import_anomaly (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_run_id uuid NOT NULL REFERENCES import_run(id) ON DELETE CASCADE,
    code text NOT NULL,
    severity text NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    source_record text,
    message text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX import_anomaly_run_idx ON import_anomaly (import_run_id);
CREATE INDEX import_anomaly_code_idx ON import_anomaly (code);

CREATE TABLE staging_km_marker (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_run_id uuid NOT NULL REFERENCES import_run(id) ON DELETE CASCADE,
    source_index integer NOT NULL CHECK (source_index >= 0),
    road_code text NOT NULL,
    kilometer integer NOT NULL CHECK (kilometer >= 0),
    raw_description text NOT NULL,
    original_geometry geometry(Point, 4326) NOT NULL,
    parse_status text NOT NULL DEFAULT 'parsed'
        CHECK (parse_status IN ('parsed', 'needs_validation', 'rejected')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (import_run_id, source_index),
    UNIQUE (import_run_id, road_code, kilometer),
    CHECK (ST_IsValid(original_geometry)),
    CHECK (ST_X(original_geometry) BETWEEN -180 AND 180),
    CHECK (ST_Y(original_geometry) BETWEEN -90 AND 90)
);

CREATE INDEX staging_km_marker_geometry_gix
    ON staging_km_marker USING gist (original_geometry);

CREATE TABLE staging_mowing_polygon (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_run_id uuid NOT NULL REFERENCES import_run(id) ON DELETE CASCADE,
    source_index integer NOT NULL CHECK (source_index >= 0),
    equipment_class text NOT NULL,
    kilometer_hint integer CHECK (kilometer_hint IS NULL OR kilometer_hint >= 0),
    raw_attributes jsonb NOT NULL,
    original_geometry geometry(Polygon, 4326) NOT NULL,
    inferred_latitude double precision,
    inferred_longitude double precision,
    inferred_area_m2 double precision CHECK (inferred_area_m2 IS NULL OR inferred_area_m2 >= 0),
    inference_status text NOT NULL DEFAULT 'needs_validation'
        CHECK (inference_status IN ('needs_validation', 'validated', 'rejected')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (import_run_id, source_index),
    CHECK (ST_IsValid(original_geometry))
);

CREATE INDEX staging_mowing_polygon_geometry_gix
    ON staging_mowing_polygon USING gist (original_geometry);

CREATE TABLE staging_vegetation_observation (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_run_id uuid NOT NULL REFERENCES import_run(id) ON DELETE CASCADE,
    version_label text NOT NULL,
    sheet_name text NOT NULL,
    reference_date date NOT NULL,
    item_code text NOT NULL,
    description text NOT NULL,
    station_meter integer NOT NULL CHECK (station_meter >= 0),
    vegetation_class text NOT NULL CHECK (vegetation_class IN ('N1', 'N2', 'N3', 'X')),
    source_cell text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (import_run_id, source_cell),
    UNIQUE (import_run_id, item_code, station_meter)
);

CREATE INDEX staging_vegetation_lookup_idx
    ON staging_vegetation_observation (reference_date, item_code, station_meter);

CREATE TABLE data_lineage (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_source_file_id uuid REFERENCES source_file(id),
    parent_import_run_id uuid REFERENCES import_run(id),
    child_entity_type text NOT NULL,
    child_entity_id text NOT NULL,
    transformation_name text NOT NULL,
    transformation_version text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(parent_source_file_id, parent_import_run_id) = 1),
    UNIQUE (
        parent_source_file_id,
        parent_import_run_id,
        child_entity_type,
        child_entity_id,
        transformation_name,
        transformation_version
    )
);

CREATE INDEX data_lineage_source_idx ON data_lineage (parent_source_file_id);
CREATE INDEX data_lineage_run_idx ON data_lineage (parent_import_run_id);
CREATE INDEX data_lineage_child_idx ON data_lineage (child_entity_type, child_entity_id);

COMMIT;
