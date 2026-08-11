BEGIN;

CREATE TABLE prepared_mowing_readiness_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL,
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    manual_assessments_are_operational boolean NOT NULL
        CHECK (NOT manual_assessments_are_operational),
    requires_operational_approval boolean NOT NULL CHECK (requires_operational_approval),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    policy_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(allowed_roles) > 0),
    CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    CHECK (jsonb_typeof(policy_metadata) = 'object')
);

INSERT INTO prepared_mowing_readiness_policy (
    id, version, allowed_roles, data_status, manual_assessments_are_operational,
    requires_operational_approval, authorizes_field_work,
    eligible_for_field_execution, policy_metadata
) VALUES (
    '96000000-0000-4000-8000-000000000001',
    'prepared-mowing-readiness-v1',
    ARRAY['manager', 'supervisor'],
    'prepared', false, true, false, false,
    '{
        "official_motiva_policy": false,
        "scope": "prepared_manual_weather_and_safety_assessment_only",
        "weather_integration_available": false,
        "official_safety_protocol_available": false,
        "clear_result_authorizes_execution": false
    }'::jsonb
);

CREATE TABLE prepared_mowing_readiness_assessment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mowing_order_id uuid NOT NULL REFERENCES prepared_mowing_order(id),
    resource_plan_id uuid NOT NULL REFERENCES prepared_mowing_resource_plan(id),
    assessed_by_user_id uuid NOT NULL REFERENCES app_user(id),
    policy_id uuid NOT NULL REFERENCES prepared_mowing_readiness_policy(id),
    supersedes_assessment_id uuid REFERENCES prepared_mowing_readiness_assessment(id),
    idempotency_key char(64) NOT NULL UNIQUE
        CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    weather_result text NOT NULL CHECK (weather_result IN ('clear', 'blocked', 'inconclusive')),
    weather_source_reference text NOT NULL CHECK (
        btrim(weather_source_reference) <> '' AND char_length(weather_source_reference) <= 500
    ),
    safety_result text NOT NULL CHECK (safety_result IN ('clear', 'blocked', 'inconclusive')),
    safety_source_reference text NOT NULL CHECK (
        btrim(safety_source_reference) <> '' AND char_length(safety_source_reference) <= 500
    ),
    assessment_rationale text NOT NULL CHECK (
        btrim(assessment_rationale) <> '' AND char_length(assessment_rationale) <= 2000
    ),
    validation_status text NOT NULL CHECK (validation_status = 'prepared_manual_pending_validation'),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    requires_operational_approval boolean NOT NULL CHECK (requires_operational_approval),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    assessed_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX prepared_mowing_readiness_supersedes_unique
    ON prepared_mowing_readiness_assessment (supersedes_assessment_id)
    WHERE supersedes_assessment_id IS NOT NULL;
CREATE INDEX prepared_mowing_readiness_order_idx
    ON prepared_mowing_readiness_assessment (resource_plan_id, assessed_at DESC);

CREATE FUNCTION validate_prepared_mowing_readiness_assessment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_proposal_id uuid;
    target_source_review_id uuid;
    target_road_id uuid;
    policy_allowed_roles text[];
    prior_count integer;
BEGIN
    SELECT mowing.proposal_id INTO target_proposal_id
    FROM prepared_mowing_order mowing
    WHERE mowing.id = NEW.mowing_order_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared readiness assessment requires a mowing order';
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

    SELECT mowing.source_review_id, axis.road_id
    INTO target_source_review_id, target_road_id
    FROM prepared_mowing_order mowing
    JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
    JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    WHERE mowing.id = NEW.mowing_order_id
      AND mowing.status = 'prepared' AND mowing.data_status = 'prepared'
      AND mowing.location_status = 'simulated'
      AND mowing.requires_operational_approval
      AND NOT mowing.authorizes_field_work
      AND NOT mowing.eligible_for_field_execution
      AND NOT mowing.eligible_for_official_reporting;

    IF NOT FOUND OR EXISTS (
        SELECT 1 FROM prepared_post_inspection_review correction
        WHERE correction.supersedes_review_id = target_source_review_id
    ) THEN
        RAISE EXCEPTION 'prepared readiness requires a current non-executable mowing order';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM prepared_mowing_resource_plan plan
        WHERE plan.id = NEW.resource_plan_id
          AND plan.mowing_order_id = NEW.mowing_order_id
          AND plan.resource_reference_status = 'prepared_placeholder_pending_validation'
          AND plan.team_assignment_status = 'unassigned'
          AND plan.equipment_assignment_status = 'unassigned'
          AND plan.requires_operational_approval
          AND NOT plan.authorizes_field_work
          AND NOT plan.eligible_for_field_execution
          AND NOT plan.eligible_for_official_reporting
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_resource_plan newer
              WHERE newer.supersedes_plan_id = plan.id
          )
    ) THEN
        RAISE EXCEPTION 'prepared readiness requires the effective resource plan';
    END IF;

    SELECT allowed_roles INTO policy_allowed_roles
    FROM prepared_mowing_readiness_policy
    WHERE id = NEW.policy_id AND data_status = 'prepared'
      AND NOT manual_assessments_are_operational
      AND requires_operational_approval
      AND NOT authorizes_field_work
      AND NOT eligible_for_field_execution;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared mowing-readiness policy is unavailable';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM app_user actor
        JOIN road_user_role assignment ON assignment.user_id = actor.id
        WHERE actor.id = NEW.assessed_by_user_id AND actor.status = 'active'
          AND assignment.road_id = target_road_id
          AND assignment.role = ANY(policy_allowed_roles)
          AND assignment.data_status <> 'simulated'
    ) THEN
        RAISE EXCEPTION 'prepared readiness actor lacks an eligible road role';
    END IF;

    SELECT count(*) INTO prior_count
    FROM prepared_mowing_readiness_assessment
    WHERE resource_plan_id = NEW.resource_plan_id;
    IF prior_count = 0 AND NEW.supersedes_assessment_id IS NOT NULL THEN
        RAISE EXCEPTION 'first prepared readiness assessment cannot supersede another assessment';
    ELSIF prior_count > 0 AND NEW.supersedes_assessment_id IS NULL THEN
        RAISE EXCEPTION 'subsequent prepared readiness assessment must supersede the effective assessment';
    ELSIF NEW.supersedes_assessment_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM prepared_mowing_readiness_assessment prior
        WHERE prior.id = NEW.supersedes_assessment_id
          AND prior.resource_plan_id = NEW.resource_plan_id
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_readiness_assessment newer
              WHERE newer.supersedes_assessment_id = prior.id
          )
    ) THEN
        RAISE EXCEPTION 'prepared readiness can only supersede its effective assessment';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_readiness_guard
BEFORE INSERT ON prepared_mowing_readiness_assessment
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_readiness_assessment();

CREATE FUNCTION prevent_prepared_mowing_readiness_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'prepared mowing readiness assessments are immutable; create a correction';
END;
$$;

CREATE TRIGGER prepared_mowing_readiness_policy_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_readiness_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mowing_readiness_mutation();
CREATE TRIGGER prepared_mowing_readiness_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_readiness_assessment
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mowing_readiness_mutation();

COMMIT;
