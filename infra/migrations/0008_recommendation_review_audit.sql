BEGIN;

CREATE TABLE recommendation_review (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    vegetation_analysis_id uuid NOT NULL REFERENCES vegetation_analysis(id),
    supersedes_review_id uuid UNIQUE REFERENCES recommendation_review(id),
    idempotency_key char(64) NOT NULL UNIQUE,
    decision text NOT NULL CHECK (decision IN ('accepted', 'rejected', 'adjusted')),
    adjusted_recommendation text
        CHECK (adjusted_recommendation IN ('monitor', 'inspect', 'mowing_review')),
    rationale text,
    reviewer_subject text NOT NULL CHECK (btrim(reviewer_subject) <> ''),
    source_channel text NOT NULL CHECK (source_channel IN ('dashboard', 'mobile', 'api')),
    review_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    reviewed_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    CHECK (supersedes_review_id IS NULL OR supersedes_review_id <> id),
    CHECK ((decision = 'adjusted') = (adjusted_recommendation IS NOT NULL)),
    CHECK (decision = 'accepted' OR btrim(COALESCE(rationale, '')) <> ''),
    CHECK (jsonb_typeof(review_metadata) = 'object')
);

CREATE INDEX recommendation_review_analysis_idx
    ON recommendation_review (vegetation_analysis_id, reviewed_at DESC, created_at DESC);
CREATE INDEX recommendation_review_reviewer_idx
    ON recommendation_review (reviewer_subject, reviewed_at DESC);

CREATE FUNCTION validate_recommendation_review_chain()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    superseded_analysis_id uuid;
BEGIN
    IF NEW.supersedes_review_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT vegetation_analysis_id
    INTO superseded_analysis_id
    FROM recommendation_review
    WHERE id = NEW.supersedes_review_id;

    IF superseded_analysis_id IS DISTINCT FROM NEW.vegetation_analysis_id THEN
        RAISE EXCEPTION 'a recommendation review can only supersede a review of the same analysis';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER recommendation_review_chain_guard
BEFORE INSERT ON recommendation_review
FOR EACH ROW EXECUTE FUNCTION validate_recommendation_review_chain();

CREATE FUNCTION prevent_recommendation_review_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'recommendation reviews are append-only; insert a superseding review';
END;
$$;

CREATE TRIGGER recommendation_review_immutable
BEFORE UPDATE OR DELETE ON recommendation_review
FOR EACH ROW EXECUTE FUNCTION prevent_recommendation_review_mutation();

COMMIT;
