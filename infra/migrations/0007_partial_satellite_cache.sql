BEGIN;

ALTER TABLE satellite_scene
    DROP CONSTRAINT satellite_scene_cache_status_check,
    DROP CONSTRAINT satellite_scene_cache_timestamp_check;

ALTER TABLE satellite_scene
    ADD CONSTRAINT satellite_scene_cache_status_check
        CHECK (cache_status IN ('discovered', 'partially_cached', 'cached')),
    ADD CONSTRAINT satellite_scene_cache_timestamp_check
        CHECK ((cache_status = 'discovered') = (cached_at IS NULL));

COMMIT;
