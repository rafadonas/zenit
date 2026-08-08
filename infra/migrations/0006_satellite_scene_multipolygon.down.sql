BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM satellite_scene
        WHERE footprint IS NOT NULL AND ST_NumGeometries(footprint) > 1
    ) THEN
        RAISE EXCEPTION
            'cannot downgrade satellite_scene footprint without discarding MultiPolygon parts';
    END IF;
END
$$;

ALTER TABLE satellite_scene
    ALTER COLUMN footprint TYPE geometry(Polygon, 4326)
    USING ST_GeometryN(footprint, 1);

COMMIT;
