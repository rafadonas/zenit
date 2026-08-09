BEGIN;

DROP TRIGGER IF EXISTS prepared_work_order_demo_event_immutable
    ON prepared_work_order_demo_event;
DROP TRIGGER IF EXISTS prepared_work_order_demo_event_guard
    ON prepared_work_order_demo_event;
DROP FUNCTION IF EXISTS validate_prepared_work_order_demo_event();
DROP TABLE IF EXISTS prepared_work_order_demo_event;

COMMIT;
