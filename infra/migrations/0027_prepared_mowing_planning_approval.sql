BEGIN;

CREATE TABLE prepared_mowing_planning_approval_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL,
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    dual_approval_requirement_status text NOT NULL
        CHECK (dual_approval_requirement_status = 'pending_official_policy_validation'),
    satisfies_operational_approval boolean NOT NULL CHECK (NOT satisfies_operational_approval),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    policy_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(allowed_roles) > 0),
    CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    CHECK (jsonb_typeof(policy_metadata) = 'object')
);

INSERT INTO prepared_mowing_planning_approval_policy (
    id, version, allowed_roles, data_status, dual_approval_requirement_status,
    satisfies_operational_approval, authorizes_field_work,
    eligible_for_field_execution, policy_metadata
) VALUES (
    '97000000-0000-4000-8000-000000000001',
    'prepared-mowing-planning-approval-v1',
    ARRAY['manager', 'supervisor'],
    'prepared', 'pending_official_policy_validation', false, false, false,
    '{
        "official_motiva_policy": false,
        "scope": "prepared_planning_approval_only",
        "critical_scenario_rules_available": false,
        "dual_approval_rules_available": false,
        "positive_decision_authorizes_execution": false
    }'::jsonb
);

CREATE TABLE prepared_mowing_planning_approval (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mowing_order_id uuid NOT NULL REFERENCES prepared_mowing_order(id),
    readiness_assessment_id uuid NOT NULL REFERENCES prepared_mowing_readiness_assessment(id),
    decided_by_user_id uuid NOT NULL REFERENCES app_user(id),
    policy_id uuid NOT NULL REFERENCES prepared_mowing_planning_approval_policy(id),
    supersedes_approval_id uuid REFERENCES prepared_mowing_planning_approval(id),
    idempotency_key char(64) NOT NULL UNIQUE
        CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    decision text NOT NULL
        CHECK (decision IN ('approved_for_planning', 'changes_requested', 'rejected')),
    decision_rationale text NOT NULL
        CHECK (btrim(decision_rationale) <> '' AND char_length(decision_rationale) <= 2000),
    approval_effect text NOT NULL
        CHECK (approval_effect = 'planning_only_no_execution_authorization'),
    dual_approval_requirement_status text NOT NULL
        CHECK (dual_approval_requirement_status = 'pending_official_policy_validation'),
    operational_approval_satisfied boolean NOT NULL CHECK (NOT operational_approval_satisfied),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    decided_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX prepared_mowing_planning_approval_supersedes_unique
    ON prepared_mowing_planning_approval (supersedes_approval_id)
    WHERE supersedes_approval_id IS NOT NULL;
CREATE INDEX prepared_mowing_planning_approval_readiness_idx
    ON prepared_mowing_planning_approval (readiness_assessment_id, decided_at DESC);

CREATE FUNCTION validate_prepared_mowing_planning_approval()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_proposal_id uuid;
    target_resource_plan_id uuid;
    target_road_id uuid;
    target_weather_result text;
    target_safety_result text;
    policy_allowed_roles text[];
    prior_count integer;
BEGIN
    SELECT mowing.proposal_id, assessment.resource_plan_id
    INTO target_proposal_id, target_resource_plan_id
    FROM prepared_mowing_order mowing
    JOIN prepared_mowing_readiness_assessment assessment
      ON assessment.mowing_order_id = mowing.id
    WHERE mowing.id = NEW.mowing_order_id
      AND assessment.id = NEW.readiness_assessment_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared planning approval requires a readiness assessment';
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-post-inspection-review:' || target_proposal_id, 0)
    );
    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-mowing-resource-plan:' || NEW.mowing_order_id, 0)
    );
    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-mowing-readiness:' || NEW.mowing_order_id, 0)
    );
    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-mowing-planning-approval:' || NEW.readiness_assessment_id, 0)
    );

    SELECT axis.road_id, assessment.weather_result, assessment.safety_result
    INTO target_road_id, target_weather_result, target_safety_result
    FROM prepared_mowing_order mowing
    JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
    JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    JOIN prepared_mowing_resource_plan plan ON plan.mowing_order_id = mowing.id
    JOIN prepared_mowing_readiness_assessment assessment
      ON assessment.resource_plan_id = plan.id
    WHERE mowing.id = NEW.mowing_order_id
      AND plan.id = target_resource_plan_id
      AND assessment.id = NEW.readiness_assessment_id
      AND NOT EXISTS (
          SELECT 1 FROM prepared_post_inspection_review correction
          WHERE correction.supersedes_review_id = mowing.source_review_id)
      AND NOT EXISTS (
          SELECT 1 FROM prepared_mowing_resource_plan newer_plan
          WHERE newer_plan.supersedes_plan_id = plan.id)
      AND NOT EXISTS (
          SELECT 1 FROM prepared_mowing_readiness_assessment newer_assessment
          WHERE newer_assessment.supersedes_assessment_id = assessment.id)
      AND assessment.validation_status = 'prepared_manual_pending_validation'
      AND assessment.requires_operational_approval
      AND NOT assessment.authorizes_field_work
      AND NOT assessment.eligible_for_field_execution
      AND NOT assessment.eligible_for_official_reporting;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared planning approval requires the effective readiness assessment';
    END IF;

    IF NEW.decision = 'approved_for_planning'
       AND (target_weather_result <> 'clear' OR target_safety_result <> 'clear') THEN
        RAISE EXCEPTION 'planning approval requires clear prepared weather and safety results';
    END IF;

    SELECT allowed_roles INTO policy_allowed_roles
    FROM prepared_mowing_planning_approval_policy
    WHERE id = NEW.policy_id AND data_status = 'prepared'
      AND dual_approval_requirement_status = 'pending_official_policy_validation'
      AND NOT satisfies_operational_approval
      AND NOT authorizes_field_work
      AND NOT eligible_for_field_execution;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared mowing planning-approval policy is unavailable';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM app_user actor
        JOIN road_user_role assignment ON assignment.user_id = actor.id
        WHERE actor.id = NEW.decided_by_user_id AND actor.status = 'active'
          AND assignment.road_id = target_road_id
          AND assignment.role = ANY(policy_allowed_roles)
          AND assignment.data_status <> 'simulated'
    ) THEN
        RAISE EXCEPTION 'prepared planning approver lacks an eligible road role';
    END IF;

    SELECT count(*) INTO prior_count
    FROM prepared_mowing_planning_approval
    WHERE readiness_assessment_id = NEW.readiness_assessment_id;
    IF prior_count = 0 AND NEW.supersedes_approval_id IS NOT NULL THEN
        RAISE EXCEPTION 'first prepared planning approval cannot supersede another approval';
    ELSIF prior_count > 0 AND NEW.supersedes_approval_id IS NULL THEN
        RAISE EXCEPTION 'subsequent prepared planning approval must supersede the effective approval';
    ELSIF NEW.supersedes_approval_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM prepared_mowing_planning_approval prior
        WHERE prior.id = NEW.supersedes_approval_id
          AND prior.readiness_assessment_id = NEW.readiness_assessment_id
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_planning_approval newer
              WHERE newer.supersedes_approval_id = prior.id)
    ) THEN
        RAISE EXCEPTION 'prepared planning approval can only supersede its effective approval';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_planning_approval_guard
BEFORE INSERT ON prepared_mowing_planning_approval
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_planning_approval();

CREATE FUNCTION prevent_prepared_mowing_planning_approval_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'prepared mowing planning approvals are immutable; create a correction';
END;
$$;
CREATE TRIGGER prepared_mowing_planning_approval_policy_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_planning_approval_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mowing_planning_approval_mutation();
CREATE TRIGGER prepared_mowing_planning_approval_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_planning_approval
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mowing_planning_approval_mutation();

COMMIT;
