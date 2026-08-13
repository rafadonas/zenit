BEGIN;

DROP TRIGGER IF EXISTS prepared_mowing_post_service_exception_policy_immutable
    ON prepared_mowing_post_service_exception_policy;
DROP TRIGGER IF EXISTS prepared_mowing_post_service_exception_immutable
    ON prepared_mowing_post_service_exception;
DROP TRIGGER IF EXISTS prepared_mowing_post_service_exception_guard
    ON prepared_mowing_post_service_exception;
DROP FUNCTION IF EXISTS validate_prepared_mowing_post_service_exception();
DROP TABLE IF EXISTS prepared_mowing_post_service_exception;
DROP TABLE IF EXISTS prepared_mowing_post_service_exception_policy;

COMMIT;
