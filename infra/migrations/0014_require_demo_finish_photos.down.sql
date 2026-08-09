BEGIN;

DROP TRIGGER IF EXISTS prepared_demo_finish_photo_guard
    ON prepared_work_order_demo_event;
DROP FUNCTION IF EXISTS validate_prepared_demo_finish_photos();

COMMIT;
