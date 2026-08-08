BEGIN;

DROP INDEX IF EXISTS satellite_scene_acquisition_idx;

ALTER TABLE satellite_scene
    DROP CONSTRAINT IF EXISTS satellite_scene_cache_timestamp_check,
    DROP CONSTRAINT IF EXISTS satellite_scene_cache_status_check;

UPDATE satellite_scene
SET cached_at = COALESCE(cached_at, discovered_at);

ALTER TABLE satellite_scene
    ALTER COLUMN cached_at SET NOT NULL,
    DROP COLUMN catalog_checksum_sha256,
    DROP COLUMN cache_status,
    DROP COLUMN discovered_at,
    DROP COLUMN collection;

COMMIT;
