-- PLANET-003: the persisted Planet catalog snapshot keeps the sensor domain,
-- stays out of the cached state and never duplicates a scene.
BEGIN;

INSERT INTO satellite_scene (
    provider,
    external_scene_id,
    collection,
    sensor,
    acquired_at,
    discovered_at,
    cached_at,
    cache_status,
    cloud_cover_percent,
    data_status,
    catalog_checksum_sha256,
    metadata
) VALUES (
    'planet',
    'planet-persistence-contract-test',
    'PSScene',
    'planet-scope',
    timestamptz '2026-08-05 13:53:00+00',
    now(),
    NULL,
    'discovered',
    1.51,
    'real',
    repeat('c', 64),
    '{"catalog_only": true}'::jsonb
);

DO $$
DECLARE
    stored satellite_scene%ROWTYPE;
BEGIN
    SELECT * INTO stored
    FROM satellite_scene
    WHERE provider = 'planet' AND external_scene_id = 'planet-persistence-contract-test';

    IF stored.cache_status <> 'discovered' OR stored.cached_at IS NOT NULL THEN
        RAISE EXCEPTION 'persisted Planet scene must stay discovered without cached_at';
    END IF;
    IF stored.catalog_checksum_sha256 IS NULL THEN
        RAISE EXCEPTION 'persisted Planet scene must keep its catalog checksum';
    END IF;
END;
$$;

-- A repeated search must not duplicate the scene or overwrite the first snapshot.
INSERT INTO satellite_scene (
    provider, external_scene_id, collection, sensor, acquired_at,
    discovered_at, cached_at, cache_status, data_status, catalog_checksum_sha256
) VALUES (
    'planet', 'planet-persistence-contract-test', 'PSScene', 'planet-scope',
    timestamptz '2026-08-05 13:53:00+00', now(), NULL, 'discovered', 'real', repeat('d', 64)
)
ON CONFLICT (provider, external_scene_id) DO NOTHING;

DO $$
BEGIN
    IF (
        SELECT count(*) FROM satellite_scene
        WHERE provider = 'planet' AND external_scene_id = 'planet-persistence-contract-test'
    ) <> 1 THEN
        RAISE EXCEPTION 'repeating the same catalog search duplicated a Planet scene';
    END IF;
    IF (
        SELECT catalog_checksum_sha256 FROM satellite_scene
        WHERE provider = 'planet' AND external_scene_id = 'planet-persistence-contract-test'
    ) <> repeat('c', 64) THEN
        RAISE EXCEPTION 'the first catalog snapshot checksum was overwritten';
    END IF;
END;
$$;

-- An unknown sensor stays rejected by the migrated domain.
DO $$
BEGIN
    BEGIN
        INSERT INTO satellite_scene (
            provider, external_scene_id, collection, sensor, acquired_at,
            discovered_at, cached_at, cache_status, data_status, catalog_checksum_sha256
        ) VALUES (
            'planet', 'planet-unknown-sensor-test', 'PSScene', 'planet-skysat',
            now(), now(), NULL, 'discovered', 'real', repeat('e', 64)
        );
        RAISE EXCEPTION 'an unknown sensor was accepted by satellite_scene';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;
END;
$$;

ROLLBACK;
