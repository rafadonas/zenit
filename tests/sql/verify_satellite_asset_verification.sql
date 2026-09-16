-- PLANET-007: the integrity audit is append-only evidence and never repairs an asset.
BEGIN;

INSERT INTO satellite_scene (
    provider, external_scene_id, collection, sensor, acquired_at, discovered_at,
    cached_at, cache_status, data_status, catalog_checksum_sha256
) VALUES (
    'planet', 'asset-verification-contract-test', 'PSScene', 'planet-scope',
    now(), now(), now(), 'cached', 'real', repeat('a', 64)
);

INSERT INTO satellite_asset (
    satellite_scene_id, asset_role, storage_uri, checksum_sha256, media_type,
    storage_version_id, size_bytes
)
SELECT id, 'ortho_analytic_4b', 's3://zenit-raw/contract/test.aesgcm', repeat('b', 64),
       'image/tiff', 'version-1', 1024
FROM satellite_scene WHERE external_scene_id = 'asset-verification-contract-test';

INSERT INTO satellite_asset_verification (
    satellite_asset_id, expected_checksum_sha256, observed_checksum_sha256,
    observed_bytes, status, verifier_version
)
SELECT id, repeat('b', 64), repeat('b', 64), 1024, 'verified', 'zenit-asset-verifier-v1'
FROM satellite_asset WHERE storage_uri = 's3://zenit-raw/contract/test.aesgcm';

-- A verified record must carry the matching checksum.
DO $$
DECLARE
    asset_id uuid;
BEGIN
    SELECT id INTO asset_id FROM satellite_asset
    WHERE storage_uri = 's3://zenit-raw/contract/test.aesgcm';
    BEGIN
        INSERT INTO satellite_asset_verification (
            satellite_asset_id, expected_checksum_sha256, observed_checksum_sha256,
            observed_bytes, status, verifier_version
        ) VALUES (asset_id, repeat('b', 64), repeat('c', 64), 1024, 'verified', 'v1');
        RAISE EXCEPTION 'a verified record was accepted with a divergent checksum';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    -- Bytes may be intact while the registered size diverges: that is a mismatch
    -- whose observed checksum equals the expected one, and it must be storable.
    INSERT INTO satellite_asset_verification (
        satellite_asset_id, expected_checksum_sha256, observed_checksum_sha256,
        observed_bytes, status, detail, verifier_version
    ) VALUES (
        asset_id, repeat('b', 64), repeat('b', 64), 2048, 'mismatch',
        'stored size does not match the registered size', 'zenit-asset-verifier-v1'
    );

    -- A mismatch always carries what was observed.
    BEGIN
        INSERT INTO satellite_asset_verification (
            satellite_asset_id, expected_checksum_sha256, observed_checksum_sha256,
            observed_bytes, status, verifier_version
        ) VALUES (asset_id, repeat('b', 64), NULL, NULL, 'mismatch', 'v1');
        RAISE EXCEPTION 'a mismatch was accepted without an observed checksum';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    -- A missing object cannot report observed bytes content.
    BEGIN
        INSERT INTO satellite_asset_verification (
            satellite_asset_id, expected_checksum_sha256, observed_checksum_sha256,
            observed_bytes, status, verifier_version
        ) VALUES (asset_id, repeat('b', 64), repeat('c', 64), 1024, 'missing', 'v1');
        RAISE EXCEPTION 'a missing record was accepted with an observed checksum';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;
END;
$$;

-- Audit records are evidence: they cannot be edited or deleted.
DO $$
BEGIN
    BEGIN
        UPDATE satellite_asset_verification SET status = 'mismatch';
        RAISE EXCEPTION 'an audit record was updated';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'satellite asset verifications are append-only' THEN RAISE; END IF;
    END;
    BEGIN
        DELETE FROM satellite_asset_verification;
        RAISE EXCEPTION 'an audit record was deleted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'satellite asset verifications are append-only' THEN RAISE; END IF;
    END;
END;
$$;

ROLLBACK;
