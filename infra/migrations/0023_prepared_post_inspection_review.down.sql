BEGIN;
DROP TRIGGER IF EXISTS prepared_post_inspection_review_immutable
    ON prepared_post_inspection_review;
DROP TRIGGER IF EXISTS prepared_post_inspection_review_guard
    ON prepared_post_inspection_review;
DROP FUNCTION IF EXISTS validate_prepared_post_inspection_review();
DROP TABLE IF EXISTS prepared_post_inspection_review;
COMMIT;
