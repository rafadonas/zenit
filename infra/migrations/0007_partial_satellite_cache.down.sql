BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM satellite_scene WHERE cache_status = 'partially_cached') THEN
        RAISE EXCEPTION 'cannot downgrade while partially cached satellite assets exist';
    END IF;
END
$$;

ALTER TABLE satellite_scene
    DROP CONSTRAINT satellite_scene_cache_status_check,
    DROP CONSTRAINT satellite_scene_cache_timestamp_check,
    ADD CONSTRAINT satellite_scene_cache_status_check
        CHECK (cache_status IN ('discovered', 'cached')),
    ADD CONSTRAINT satellite_scene_cache_timestamp_check
        CHECK ((cache_status = 'cached') = (cached_at IS NOT NULL));

COMMIT;
