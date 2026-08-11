BEGIN;

DROP TRIGGER IF EXISTS prepared_inspection_summary_export_event_immutable
    ON prepared_inspection_summary_export_event;
DROP TRIGGER IF EXISTS prepared_inspection_summary_export_event_guard
    ON prepared_inspection_summary_export_event;
DROP FUNCTION IF EXISTS validate_prepared_inspection_summary_export_event();
DROP TABLE IF EXISTS prepared_inspection_summary_export_event;

COMMIT;
