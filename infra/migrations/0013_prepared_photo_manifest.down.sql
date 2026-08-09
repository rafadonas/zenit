BEGIN;

DROP TRIGGER IF EXISTS prepared_field_photo_manifest_immutable
    ON prepared_field_photo_manifest;
DROP TRIGGER IF EXISTS prepared_field_photo_manifest_guard
    ON prepared_field_photo_manifest;
DROP FUNCTION IF EXISTS validate_prepared_field_photo_manifest();
DROP TABLE IF EXISTS prepared_field_photo_manifest;

COMMIT;
