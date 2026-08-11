BEGIN;

DROP TRIGGER IF EXISTS prepared_photo_review_policy_immutable
    ON prepared_photo_review_policy;
DROP TRIGGER IF EXISTS prepared_photo_human_review_immutable
    ON prepared_photo_human_review;
DROP TRIGGER IF EXISTS prepared_photo_human_review_guard
    ON prepared_photo_human_review;
DROP FUNCTION IF EXISTS validate_prepared_photo_human_review();
DROP TABLE IF EXISTS prepared_photo_human_review;
DROP TABLE IF EXISTS prepared_photo_review_policy;

COMMIT;
