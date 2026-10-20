BEGIN;

ALTER TABLE satellite_asset
    ADD COLUMN storage_version_id text,
    ADD COLUMN size_bytes bigint CHECK (size_bytes IS NULL OR size_bytes >= 0);

COMMENT ON COLUMN satellite_asset.storage_version_id IS
    'Object version that carries the verified bytes; NULL for assets stored before PLANET-007';

CREATE TABLE satellite_asset_verification (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    satellite_asset_id uuid NOT NULL REFERENCES satellite_asset(id) ON DELETE CASCADE,
    checked_at timestamptz NOT NULL DEFAULT now(),
    expected_checksum_sha256 char(64) NOT NULL,
    observed_checksum_sha256 char(64),
    observed_bytes bigint CHECK (observed_bytes IS NULL OR observed_bytes >= 0),
    status text NOT NULL CHECK (status IN ('verified', 'mismatch', 'missing', 'unreadable')),
    detail text,
    verifier_version text NOT NULL,
    CHECK ((status = 'verified') = (observed_checksum_sha256 = expected_checksum_sha256)),
    CHECK (status <> 'missing' OR observed_checksum_sha256 IS NULL)
);

COMMENT ON TABLE satellite_asset_verification IS
    'Append-only integrity audit of stored satellite assets; never corrects an asset';

CREATE INDEX satellite_asset_verification_asset_idx
    ON satellite_asset_verification (satellite_asset_id, checked_at DESC);

CREATE FUNCTION prevent_satellite_asset_verification_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'satellite asset verifications are append-only';
END;
$$;

CREATE TRIGGER satellite_asset_verification_immutable
    BEFORE UPDATE OR DELETE ON satellite_asset_verification
    FOR EACH ROW EXECUTE FUNCTION prevent_satellite_asset_verification_mutation();

COMMIT;
