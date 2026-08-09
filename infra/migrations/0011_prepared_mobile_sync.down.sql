BEGIN;

DROP TRIGGER IF EXISTS prepared_field_measurement_immutable ON prepared_field_measurement;
DROP TRIGGER IF EXISTS mobile_sync_conflict_immutable ON mobile_sync_conflict;
DROP TRIGGER IF EXISTS mobile_sync_event_immutable ON mobile_sync_event;
DROP TRIGGER IF EXISTS mobile_sync_batch_immutable ON mobile_sync_batch;
DROP TRIGGER IF EXISTS mobile_device_revocation_immutable ON mobile_device_revocation;
DROP TRIGGER IF EXISTS mobile_device_registration_immutable ON mobile_device_registration;
DROP FUNCTION IF EXISTS prevent_prepared_mobile_sync_mutation();
DROP TRIGGER IF EXISTS prepared_field_measurement_guard ON prepared_field_measurement;
DROP FUNCTION IF EXISTS validate_prepared_field_measurement();
DROP TRIGGER IF EXISTS mobile_sync_batch_guard ON mobile_sync_batch;
DROP FUNCTION IF EXISTS validate_mobile_sync_batch();
DROP TRIGGER IF EXISTS mobile_device_registration_guard ON mobile_device_registration;
DROP FUNCTION IF EXISTS validate_mobile_device_registration();
DROP TABLE IF EXISTS prepared_field_measurement;
DROP TABLE IF EXISTS mobile_sync_conflict;
DROP TABLE IF EXISTS mobile_sync_event;
DROP TABLE IF EXISTS mobile_sync_batch;
DROP SEQUENCE IF EXISTS mobile_sync_cursor_seq;
DROP TABLE IF EXISTS mobile_device_revocation;
DROP TABLE IF EXISTS mobile_device_registration;

COMMIT;
