BEGIN;

CREATE TABLE prepared_post_inspection_review (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id uuid NOT NULL REFERENCES prepared_post_inspection_proposal(id),
    reviewer_user_id uuid NOT NULL REFERENCES app_user(id),
    policy_id uuid NOT NULL REFERENCES prepared_post_inspection_policy(id),
    supersedes_review_id uuid REFERENCES prepared_post_inspection_review(id),
    idempotency_key char(64) NOT NULL UNIQUE
        CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    decision text NOT NULL CHECK (decision IN ('accepted', 'rejected', 'adjusted')),
    adjusted_recommendation text
        CHECK (adjusted_recommendation IN ('monitor', 'mowing_review')),
    rationale text CHECK (rationale IS NULL OR char_length(rationale) <= 2000),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    eligible_for_official_reporting boolean NOT NULL
        CHECK (NOT eligible_for_official_reporting),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    reviewed_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((decision = 'adjusted') = (adjusted_recommendation IS NOT NULL)),
    CONSTRAINT prepared_post_inspection_review_rationale_required CHECK (
        decision = 'accepted' OR (rationale IS NOT NULL AND btrim(rationale) <> '')
    )
);

CREATE UNIQUE INDEX prepared_post_inspection_review_supersedes_unique
    ON prepared_post_inspection_review (supersedes_review_id)
    WHERE supersedes_review_id IS NOT NULL;
CREATE INDEX prepared_post_inspection_review_proposal_idx
    ON prepared_post_inspection_review (proposal_id, reviewed_at DESC);

CREATE FUNCTION validate_prepared_post_inspection_review()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE prior_count integer;
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-post-inspection-review:' || NEW.proposal_id, 0)
    );

    IF NOT EXISTS (
        SELECT 1
        FROM prepared_post_inspection_proposal proposal
        JOIN prepared_inspection_summary summary ON summary.id = proposal.summary_id
        JOIN work_order order_record ON order_record.id = summary.work_order_id
        JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN prepared_post_inspection_policy policy ON policy.id = NEW.policy_id
        JOIN app_user reviewer ON reviewer.id = NEW.reviewer_user_id
        WHERE proposal.id = NEW.proposal_id
          AND proposal.policy_id = policy.id
          AND proposal.requires_human_review
          AND proposal.data_status = 'prepared'
          AND NOT proposal.eligible_for_official_reporting
          AND NOT proposal.authorizes_field_work
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
        RAISE EXCEPTION 'prepared proposal review requires exact policy and road role';
    END IF;

    SELECT count(*) INTO prior_count
    FROM prepared_post_inspection_review
    WHERE proposal_id = NEW.proposal_id;

    IF prior_count = 0 AND NEW.supersedes_review_id IS NOT NULL THEN
        RAISE EXCEPTION 'first prepared proposal review cannot supersede another review';
    ELSIF prior_count > 0 AND NEW.supersedes_review_id IS NULL THEN
        RAISE EXCEPTION 'subsequent prepared proposal review must supersede the effective review';
    ELSIF NEW.supersedes_review_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM prepared_post_inspection_review prior
        WHERE prior.id = NEW.supersedes_review_id
          AND prior.proposal_id = NEW.proposal_id
          AND NOT EXISTS (
              SELECT 1 FROM prepared_post_inspection_review newer
              WHERE newer.supersedes_review_id = prior.id
          )
    ) THEN
        RAISE EXCEPTION 'prepared proposal review can only supersede its effective review';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_post_inspection_review_guard
BEFORE INSERT ON prepared_post_inspection_review
FOR EACH ROW EXECUTE FUNCTION validate_prepared_post_inspection_review();
CREATE TRIGGER prepared_post_inspection_review_immutable
BEFORE UPDATE OR DELETE ON prepared_post_inspection_review
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
