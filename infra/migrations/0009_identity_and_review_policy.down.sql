BEGIN;

DROP TRIGGER IF EXISTS recommendation_review_identity_policy_guard ON recommendation_review;
DROP FUNCTION IF EXISTS validate_recommendation_review_identity_and_policy();
DROP TRIGGER IF EXISTS recommendation_review_policy_immutable ON recommendation_review_policy;
DROP FUNCTION IF EXISTS prevent_recommendation_review_policy_mutation();
ALTER TABLE recommendation_review
    DROP CONSTRAINT IF EXISTS recommendation_review_identity_consistency,
    DROP COLUMN IF EXISTS review_policy_id,
    DROP COLUMN IF EXISTS reviewer_user_id;
DROP TABLE IF EXISTS recommendation_review_policy;
DROP TABLE IF EXISTS road_user_role;
DROP TABLE IF EXISTS app_user;

COMMIT;
