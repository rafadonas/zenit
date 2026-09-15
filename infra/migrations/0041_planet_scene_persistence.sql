BEGIN;

ALTER TABLE satellite_scene
    DROP CONSTRAINT IF EXISTS satellite_scene_sensor_check;

ALTER TABLE satellite_scene
    ADD CONSTRAINT satellite_scene_sensor_check
    CHECK (sensor IN ('sentinel-2', 'cbers-4a', 'planet-scope'));

COMMENT ON COLUMN satellite_scene.sensor IS
    'Provider sensor identifier; PlanetScope remains a separate product series';

COMMIT;
