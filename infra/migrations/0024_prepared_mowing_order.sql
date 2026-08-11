BEGIN;

CREATE TABLE prepared_mowing_order_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL,
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    requires_team_assignment boolean NOT NULL CHECK (requires_team_assignment),
    requires_operational_approval boolean NOT NULL CHECK (requires_operational_approval),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    policy_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(allowed_roles) > 0),
    CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    CHECK (jsonb_typeof(policy_metadata) = 'object')
);

INSERT INTO prepared_mowing_order_policy (
    id, version, allowed_roles, data_status, requires_team_assignment,
    requires_operational_approval, authorizes_field_work,
    eligible_for_field_execution, policy_metadata
) VALUES (
    '94000000-0000-4000-8000-000000000001',
    'prepared-mowing-order-v1',
    ARRAY['manager', 'supervisor'],
    'prepared', true, true, false, false,
    '{
        "official_motiva_policy": false,
        "scope": "prepared_mowing_order_foundation_only",
        "team_assignment_implemented": false,
        "equipment_assignment_implemented": false,
        "weather_and_safety_clearance_implemented": false
    }'::jsonb
);

CREATE TABLE prepared_mowing_order (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id uuid NOT NULL REFERENCES prepared_post_inspection_proposal(id),
    source_review_id uuid NOT NULL UNIQUE REFERENCES prepared_post_inspection_review(id),
    source_inspection_work_order_id uuid NOT NULL REFERENCES work_order(id),
    creation_policy_id uuid NOT NULL REFERENCES prepared_mowing_order_policy(id),
    created_by_user_id uuid NOT NULL REFERENCES app_user(id),
    idempotency_key char(64) NOT NULL UNIQUE
        CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    order_type text NOT NULL CHECK (order_type = 'mowing'),
    status text NOT NULL CHECK (status = 'prepared'),
    version integer NOT NULL CHECK (version = 1),
    planning_rationale text NOT NULL
        CHECK (btrim(planning_rationale) <> '' AND char_length(planning_rationale) <= 2000),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    location_status text NOT NULL CHECK (location_status = 'simulated'),
    source_evidence_status text NOT NULL
        CHECK (source_evidence_status = 'prepared_reviewed_non_operational'),
    team_assignment_status text NOT NULL CHECK (team_assignment_status = 'unassigned'),
    equipment_assignment_status text NOT NULL CHECK (equipment_assignment_status = 'unassigned'),
    weather_check_status text NOT NULL CHECK (weather_check_status = 'pending'),
    safety_check_status text NOT NULL CHECK (safety_check_status = 'pending'),
    requires_operational_approval boolean NOT NULL CHECK (requires_operational_approval),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX prepared_mowing_order_proposal_idx
    ON prepared_mowing_order (proposal_id, created_at DESC);
CREATE INDEX prepared_mowing_order_creator_idx
    ON prepared_mowing_order (created_by_user_id, created_at DESC);

CREATE FUNCTION validate_prepared_mowing_order()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_proposal_id uuid;
    target_inspection_work_order_id uuid;
    target_road_id uuid;
    effective_recommendation text;
    policy_allowed_roles text[];
BEGIN
    SELECT
        proposal.id,
        summary.work_order_id,
        axis.road_id,
        CASE
            WHEN review.decision = 'accepted' THEN proposal.recommendation
            WHEN review.decision = 'adjusted' THEN review.adjusted_recommendation
            ELSE NULL
        END
    INTO target_proposal_id, target_inspection_work_order_id, target_road_id,
         effective_recommendation
    FROM prepared_post_inspection_review review
    JOIN prepared_post_inspection_proposal proposal ON proposal.id = review.proposal_id
    JOIN prepared_inspection_summary summary ON summary.id = proposal.summary_id
    JOIN work_order order_record ON order_record.id = summary.work_order_id
    JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    WHERE review.id = NEW.source_review_id
      AND review.policy_id = proposal.policy_id
      AND review.data_status = 'prepared'
      AND NOT review.eligible_for_official_reporting
      AND NOT review.authorizes_field_work
      AND proposal.data_status = 'prepared'
      AND proposal.location_status = 'simulated'
      AND proposal.evidence_status = 'prepared_reviewed_non_operational'
      AND NOT proposal.eligible_for_official_reporting
      AND NOT proposal.authorizes_field_work;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared mowing order requires a safe versioned source review';
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-post-inspection-review:' || target_proposal_id, 0)
    );

    IF EXISTS (
        SELECT 1 FROM prepared_post_inspection_review correction
        WHERE correction.supersedes_review_id = NEW.source_review_id
    ) THEN
        RAISE EXCEPTION 'prepared mowing order requires the effective proposal review';
    END IF;

    IF effective_recommendation IS DISTINCT FROM 'mowing_review' THEN
        RAISE EXCEPTION 'only an effective mowing-review decision can create a mowing order';
    END IF;

    IF NEW.proposal_id <> target_proposal_id
       OR NEW.source_inspection_work_order_id <> target_inspection_work_order_id THEN
        RAISE EXCEPTION 'prepared mowing order must preserve its proposal and inspection order';
    END IF;

    SELECT allowed_roles INTO policy_allowed_roles
    FROM prepared_mowing_order_policy
    WHERE id = NEW.creation_policy_id
      AND data_status = 'prepared'
      AND requires_team_assignment
      AND requires_operational_approval
      AND NOT authorizes_field_work
      AND NOT eligible_for_field_execution;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared mowing-order policy is unavailable';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM app_user creator
        JOIN road_user_role assignment ON assignment.user_id = creator.id
        WHERE creator.id = NEW.created_by_user_id
          AND creator.status = 'active'
          AND assignment.road_id = target_road_id
          AND assignment.role = ANY(policy_allowed_roles)
          AND assignment.data_status <> 'simulated'
    ) THEN
        RAISE EXCEPTION 'prepared mowing-order creator lacks an eligible road role';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_order_guard
BEFORE INSERT ON prepared_mowing_order
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_order();

CREATE FUNCTION prevent_prepared_mowing_order_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'prepared mowing orders are immutable; create a new reviewed event';
END;
$$;

CREATE TRIGGER prepared_mowing_order_policy_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_order_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mowing_order_mutation();

CREATE TRIGGER prepared_mowing_order_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_order
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mowing_order_mutation();

COMMIT;
