BEGIN;

CREATE TABLE planet_order (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    external_order_id text NOT NULL UNIQUE,
    order_name text NOT NULL,
    source_type text NOT NULL CHECK (source_type = 'scenes'),
    item_type text NOT NULL CHECK (item_type = 'PSScene'),
    item_ids jsonb NOT NULL,
    product_bundle text NOT NULL CHECK (product_bundle = 'analytic_udm2'),
    aoi geometry(Polygon, 4326) NOT NULL,
    aoi_area_m2 numeric(12, 2) NOT NULL CHECK (aoi_area_m2 > 0 AND aoi_area_m2 <= 10000.00),
    max_bytes bigint NOT NULL CHECK (max_bytes > 0 AND max_bytes <= 104857600),
    downloaded_bytes bigint NOT NULL DEFAULT 0 CHECK (downloaded_bytes >= 0),
    license_scope text NOT NULL CHECK (license_scope = 'academic-only'),
    retention_days integer NOT NULL CHECK (retention_days BETWEEN 1 AND 365),
    destination_bucket text NOT NULL,
    destination_prefix text NOT NULL,
    request_checksum_sha256 char(64) NOT NULL UNIQUE,
    order_state text NOT NULL DEFAULT 'queued'
        CHECK (order_state IN ('queued', 'running', 'success', 'failed', 'cancelled')),
    response_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    data_status text NOT NULL DEFAULT 'real'
        CHECK (data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')),
    eligible_for_operations boolean NOT NULL DEFAULT false,
    eligible_for_official_reporting boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CHECK (ST_IsValid(aoi)),
    CHECK (downloaded_bytes <= max_bytes),
    CHECK (data_status = 'real' OR NOT eligible_for_official_reporting),
    CHECK (NOT eligible_for_operations)
);

CREATE INDEX planet_order_state_idx ON planet_order (order_state, created_at DESC);

ALTER TABLE satellite_asset
    ADD COLUMN source_order_id uuid REFERENCES planet_order(id);

CREATE TABLE planet_order_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    planet_order_id uuid NOT NULL REFERENCES planet_order(id) ON DELETE CASCADE,
    event_type text NOT NULL CHECK (event_type IN ('created', 'status', 'asset_downloaded', 'failed')),
    order_state text NOT NULL
        CHECK (order_state IN ('queued', 'running', 'success', 'failed', 'cancelled')),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX planet_order_event_order_idx
    ON planet_order_event (planet_order_id, occurred_at DESC);

CREATE FUNCTION prevent_planet_order_event_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Planet Order events are append-only';
END;
$$;

CREATE TRIGGER planet_order_event_immutable
BEFORE UPDATE OR DELETE ON planet_order_event
FOR EACH ROW EXECUTE FUNCTION prevent_planet_order_event_mutation();

COMMIT;
