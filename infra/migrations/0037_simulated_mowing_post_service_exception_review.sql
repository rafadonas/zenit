BEGIN;

CREATE TABLE prepared_mowing_post_service_exception_review (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    exception_id uuid NOT NULL REFERENCES prepared_mowing_post_service_exception(id),
    reviewer_user_id uuid NOT NULL REFERENCES app_user(id),
    policy_id uuid NOT NULL REFERENCES prepared_mowing_post_service_exception_policy(id),
    supersedes_review_id uuid REFERENCES prepared_mowing_post_service_exception_review(id),
    idempotency_key char(64) NOT NULL UNIQUE CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    decision text NOT NULL CHECK (decision IN ('accepted', 'rejected', 'adjusted')),
    adjusted_recommendation text CHECK (adjusted_recommendation IN ('monitor', 'inspect_follow_up')),
    rationale text CHECK (rationale IS NULL OR char_length(rationale) <= 2000),
    phase text NOT NULL CHECK (phase = 'post_service'),
    data_status text NOT NULL CHECK (data_status = 'simulated'),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    reviewed_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((decision = 'adjusted') = (adjusted_recommendation IS NOT NULL)),
    CONSTRAINT prepared_mowing_exception_review_rationale_required CHECK (
        decision = 'accepted' OR (rationale IS NOT NULL AND btrim(rationale) <> '')
    )
);

CREATE UNIQUE INDEX prepared_mowing_exception_review_supersedes_unique
    ON prepared_mowing_post_service_exception_review (supersedes_review_id)
    WHERE supersedes_review_id IS NOT NULL;
CREATE INDEX prepared_mowing_exception_review_exception_idx
    ON prepared_mowing_post_service_exception_review (exception_id, reviewed_at DESC);

CREATE FUNCTION validate_prepared_mowing_post_service_exception_review()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior_count integer;
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtextextended('mowing-post-service-exception-review:' || NEW.exception_id, 0)
    );

    IF NOT EXISTS (
        SELECT 1
        FROM prepared_mowing_post_service_exception exception
        JOIN prepared_mowing_post_service_summary summary ON summary.id = exception.summary_id
        JOIN prepared_mowing_order mowing ON mowing.id = summary.mowing_order_id
        JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
        JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN prepared_mowing_post_service_exception_policy policy ON policy.id = NEW.policy_id
        JOIN app_user reviewer ON reviewer.id = NEW.reviewer_user_id
        WHERE exception.id = NEW.exception_id
          AND exception.policy_id = policy.id
          AND exception.requires_human_review
          AND exception.phase = 'post_service'
          AND exception.data_status = 'simulated'
          AND NOT exception.eligible_for_official_reporting
          AND NOT exception.authorizes_field_work
          AND policy.data_status = 'prepared'
          AND policy.requires_human_review
          AND NOT policy.authorizes_field_work
          AND reviewer.status = 'active'
          AND EXISTS (
              SELECT 1 FROM road_user_role assignment
              WHERE assignment.user_id = reviewer.id
                AND assignment.road_id = axis.road_id
                AND assignment.role = ANY(policy.allowed_roles)
                AND assignment.data_status <> 'simulated'
          )
    ) THEN
        RAISE EXCEPTION 'post-service exception review requires exact policy and road role';
    END IF;

    SELECT count(*) INTO prior_count
    FROM prepared_mowing_post_service_exception_review
    WHERE exception_id = NEW.exception_id;

    IF prior_count = 0 AND NEW.supersedes_review_id IS NOT NULL THEN
        RAISE EXCEPTION 'first post-service exception review cannot supersede another review';
    ELSIF prior_count > 0 AND NEW.supersedes_review_id IS NULL THEN
        RAISE EXCEPTION 'subsequent post-service exception review must supersede effective review';
    ELSIF NEW.supersedes_review_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM prepared_mowing_post_service_exception_review prior
        WHERE prior.id = NEW.supersedes_review_id
          AND prior.exception_id = NEW.exception_id
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_post_service_exception_review newer
              WHERE newer.supersedes_review_id = prior.id
          )
    ) THEN
        RAISE EXCEPTION 'post-service exception review can only supersede effective review';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_post_service_exception_review_guard
BEFORE INSERT ON prepared_mowing_post_service_exception_review
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_post_service_exception_review();
CREATE TRIGGER prepared_mowing_post_service_exception_review_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_exception_review
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
