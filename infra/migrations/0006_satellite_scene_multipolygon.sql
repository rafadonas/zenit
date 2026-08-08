BEGIN;

ALTER TABLE satellite_scene
    ALTER COLUMN footprint TYPE geometry(MultiPolygon, 4326)
    USING ST_Multi(footprint);

COMMIT;
