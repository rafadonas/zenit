BEGIN;
DROP TRIGGER IF EXISTS prepared_mowing_post_service_measurement_immutable
    ON prepared_mowing_post_service_measurement;
DROP TRIGGER IF EXISTS prepared_mowing_post_service_measurement_guard
    ON prepared_mowing_post_service_measurement;
DROP FUNCTION IF EXISTS validate_prepared_mowing_post_service_measurement();
DROP TABLE IF EXISTS prepared_mowing_post_service_measurement;
COMMIT;
