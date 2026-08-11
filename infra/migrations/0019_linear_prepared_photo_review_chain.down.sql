BEGIN;
DROP TRIGGER IF EXISTS prepared_photo_human_review_linear_guard
    ON prepared_photo_human_review;
DROP FUNCTION IF EXISTS validate_linear_prepared_photo_review_chain();
COMMIT;
