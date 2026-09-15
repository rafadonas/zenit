BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM satellite_scene WHERE sensor = 'planet-scope') THEN
        RAISE EXCEPTION 'cannot revert Planet sensor support while Planet scenes exist';
    END IF;
END;
$$;

ALTER TABLE satellite_scene
    DROP CONSTRAINT IF EXISTS satellite_scene_sensor_check;

ALTER TABLE satellite_scene
    ADD CONSTRAINT satellite_scene_sensor_check
    CHECK (sensor IN ('sentinel-2', 'cbers-4a'));

COMMIT;
