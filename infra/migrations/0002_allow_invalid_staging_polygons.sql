BEGIN;

-- Staging preserves source evidence. Invalid source topology is reported as an
-- import anomaly and repaired only in a versioned derived layer.
ALTER TABLE staging_mowing_polygon
    DROP CONSTRAINT staging_mowing_polygon_original_geometry_check;

COMMIT;
