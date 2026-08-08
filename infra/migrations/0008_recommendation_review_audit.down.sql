BEGIN;

DROP TRIGGER IF EXISTS recommendation_review_immutable ON recommendation_review;
DROP FUNCTION IF EXISTS prevent_recommendation_review_mutation();
DROP TRIGGER IF EXISTS recommendation_review_chain_guard ON recommendation_review;
DROP FUNCTION IF EXISTS validate_recommendation_review_chain();
DROP TABLE IF EXISTS recommendation_review;

COMMIT;
