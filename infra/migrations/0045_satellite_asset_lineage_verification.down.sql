BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM satellite_asset_verification) THEN
        RAISE EXCEPTION 'cannot drop satellite asset verifications while audit records exist';
    END IF;
END;
$$;

DROP TRIGGER IF EXISTS satellite_asset_verification_immutable ON satellite_asset_verification;
DROP FUNCTION IF EXISTS prevent_satellite_asset_verification_mutation();
DROP TABLE satellite_asset_verification;

ALTER TABLE satellite_asset
    DROP COLUMN storage_version_id,
    DROP COLUMN size_bytes;

COMMIT;
