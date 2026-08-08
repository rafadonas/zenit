BEGIN;

ALTER TABLE satellite_scene
    ALTER COLUMN cached_at DROP NOT NULL,
    ADD COLUMN collection text,
    ADD COLUMN discovered_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN cache_status text NOT NULL DEFAULT 'discovered',
    ADD COLUMN catalog_checksum_sha256 char(64);

UPDATE satellite_scene
SET collection = CASE sensor
        WHEN 'sentinel-2' THEN 'sentinel-2-l2a'
        WHEN 'cbers-4a' THEN 'cbers-4a-unknown'
    END,
    cache_status = CASE WHEN cached_at IS NULL THEN 'discovered' ELSE 'cached' END,
    catalog_checksum_sha256 = encode(
        digest(
            concat_ws(
                '|',
                provider,
                external_scene_id,
                sensor,
                acquired_at::text,
                metadata::text
            ),
            'sha256'
        ),
        'hex'
    );

ALTER TABLE satellite_scene
    ALTER COLUMN collection SET NOT NULL,
    ALTER COLUMN catalog_checksum_sha256 SET NOT NULL,
    ADD CONSTRAINT satellite_scene_cache_status_check
        CHECK (cache_status IN ('discovered', 'cached')),
    ADD CONSTRAINT satellite_scene_cache_timestamp_check
        CHECK ((cache_status = 'cached') = (cached_at IS NOT NULL));

CREATE INDEX satellite_scene_acquisition_idx
    ON satellite_scene (sensor, collection, acquired_at DESC);

COMMIT;
