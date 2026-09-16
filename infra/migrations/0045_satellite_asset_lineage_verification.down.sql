BEGIN;

-- Reverting discards integrity evidence. It requires an explicit confirmation in
-- the same session, so it can never happen by accident:
--   psql -c "SET zenit.confirm_destructive = 'satellite_asset_verification'" \
--        -f infra/migrations/0045_satellite_asset_lineage_verification.down.sql
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM satellite_asset_verification)
       AND coalesce(current_setting('zenit.confirm_destructive', true), '')
           <> 'satellite_asset_verification'
    THEN
        RAISE EXCEPTION
            'cannot drop satellite asset verifications while audit records exist; '
            'set zenit.confirm_destructive to satellite_asset_verification to confirm';
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
