BEGIN;
DROP TRIGGER IF EXISTS prepared_mowing_demo_event_immutable ON prepared_mowing_demo_event;
DROP TRIGGER IF EXISTS prepared_mowing_demo_event_guard ON prepared_mowing_demo_event;
DROP FUNCTION IF EXISTS validate_prepared_mowing_demo_event();
DROP TABLE IF EXISTS prepared_mowing_demo_event;
COMMIT;
