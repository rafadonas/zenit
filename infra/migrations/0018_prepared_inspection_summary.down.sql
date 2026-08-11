BEGIN;
DROP TRIGGER IF EXISTS prepared_inspection_summary_policy_immutable ON prepared_inspection_summary_policy;
DROP TRIGGER IF EXISTS prepared_inspection_summary_immutable ON prepared_inspection_summary;
DROP TRIGGER IF EXISTS prepared_inspection_summary_guard ON prepared_inspection_summary;
DROP FUNCTION IF EXISTS validate_prepared_inspection_summary();
DROP TABLE IF EXISTS prepared_inspection_summary;
DROP TABLE IF EXISTS prepared_inspection_summary_policy;
COMMIT;
