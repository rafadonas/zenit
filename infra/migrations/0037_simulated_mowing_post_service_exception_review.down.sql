BEGIN;

DROP TRIGGER IF EXISTS prepared_mowing_post_service_exception_review_immutable
    ON prepared_mowing_post_service_exception_review;
DROP TRIGGER IF EXISTS prepared_mowing_post_service_exception_review_guard
    ON prepared_mowing_post_service_exception_review;
DROP FUNCTION IF EXISTS validate_prepared_mowing_post_service_exception_review();
DROP TABLE IF EXISTS prepared_mowing_post_service_exception_review;

COMMIT;
