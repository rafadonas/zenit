BEGIN;

DROP TRIGGER IF EXISTS prepared_photo_access_event_immutable
    ON prepared_photo_access_event;
DROP TRIGGER IF EXISTS prepared_photo_access_event_guard
    ON prepared_photo_access_event;
DROP FUNCTION IF EXISTS validate_prepared_photo_access_event();
DROP TABLE IF EXISTS prepared_photo_access_event;

COMMIT;
