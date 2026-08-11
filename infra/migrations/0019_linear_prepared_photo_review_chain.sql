BEGIN;

CREATE FUNCTION validate_linear_prepared_photo_review_chain()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    prior_count integer;
BEGIN
    SELECT count(*) INTO prior_count
    FROM prepared_photo_human_review
    WHERE photo_id = NEW.photo_id;

    IF prior_count = 0 AND NEW.supersedes_review_id IS NOT NULL THEN
        RAISE EXCEPTION 'first prepared photo review cannot supersede another review';
    ELSIF prior_count > 0 AND NEW.supersedes_review_id IS NULL THEN
        RAISE EXCEPTION 'subsequent prepared photo review must supersede the effective review';
    ELSIF prior_count > 0 AND EXISTS (
        SELECT 1 FROM prepared_photo_human_review newer
        WHERE newer.supersedes_review_id = NEW.supersedes_review_id
    ) THEN
        RAISE EXCEPTION 'prepared photo review can only supersede the effective leaf';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_photo_human_review_linear_guard
BEFORE INSERT ON prepared_photo_human_review
FOR EACH ROW EXECUTE FUNCTION validate_linear_prepared_photo_review_chain();

COMMIT;
