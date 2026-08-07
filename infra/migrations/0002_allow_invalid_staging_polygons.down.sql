BEGIN;

-- NOT VALID preserves already imported evidence while restoring validation for
-- future rows if this migration is rolled back.
ALTER TABLE staging_mowing_polygon
    ADD CONSTRAINT staging_mowing_polygon_original_geometry_check
    CHECK (ST_IsValid(original_geometry)) NOT VALID;

COMMIT;
