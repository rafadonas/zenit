BEGIN;

CREATE TABLE prepared_mowing_resource_plan_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL,
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    resource_references_are_verified boolean NOT NULL
        CHECK (NOT resource_references_are_verified),
    requires_operational_approval boolean NOT NULL CHECK (requires_operational_approval),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    policy_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(allowed_roles) > 0),
    CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    CHECK (jsonb_typeof(policy_metadata) = 'object')
);

INSERT INTO prepared_mowing_resource_plan_policy (
    id, version, allowed_roles, data_status, resource_references_are_verified,
    requires_operational_approval, authorizes_field_work,
    eligible_for_field_execution, policy_metadata
) VALUES (
    '95000000-0000-4000-8000-000000000001',
    'prepared-mowing-resource-plan-v1',
    ARRAY['manager', 'supervisor'],
    'prepared', false, true, false, false,
    '{
        "official_motiva_policy": false,
        "scope": "prepared_candidate_resource_references_only",
        "team_catalog_available": false,
        "equipment_catalog_available": false,
        "references_require_external_validation": true
    }'::jsonb
);

CREATE TABLE prepared_mowing_resource_plan (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mowing_order_id uuid NOT NULL REFERENCES prepared_mowing_order(id),
    created_by_user_id uuid NOT NULL REFERENCES app_user(id),
    policy_id uuid NOT NULL REFERENCES prepared_mowing_resource_plan_policy(id),
    supersedes_plan_id uuid REFERENCES prepared_mowing_resource_plan(id),
    idempotency_key char(64) NOT NULL UNIQUE
        CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    team_reference text NOT NULL
        CHECK (btrim(team_reference) <> '' AND char_length(team_reference) <= 200),
    equipment_reference text NOT NULL
        CHECK (btrim(equipment_reference) <> '' AND char_length(equipment_reference) <= 200),
    planning_rationale text NOT NULL
        CHECK (btrim(planning_rationale) <> '' AND char_length(planning_rationale) <= 2000),
    resource_reference_status text NOT NULL
        CHECK (resource_reference_status = 'prepared_placeholder_pending_validation'),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    team_assignment_status text NOT NULL CHECK (team_assignment_status = 'unassigned'),
    equipment_assignment_status text NOT NULL CHECK (equipment_assignment_status = 'unassigned'),
    requires_operational_approval boolean NOT NULL CHECK (requires_operational_approval),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX prepared_mowing_resource_plan_supersedes_unique
    ON prepared_mowing_resource_plan (supersedes_plan_id)
    WHERE supersedes_plan_id IS NOT NULL;
CREATE INDEX prepared_mowing_resource_plan_order_idx
    ON prepared_mowing_resource_plan (mowing_order_id, created_at DESC);

CREATE FUNCTION validate_prepared_mowing_resource_plan()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_road_id uuid;
    target_source_review_id uuid;
    target_proposal_id uuid;
    policy_allowed_roles text[];
    prior_count integer;
BEGIN
    SELECT proposal_id INTO target_proposal_id
    FROM prepared_mowing_order
    WHERE id = NEW.mowing_order_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared resource plan requires a mowing order';
    END IF;

    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-post-inspection-review:' || target_proposal_id, 0)
    );
    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-mowing-resource-plan:' || NEW.mowing_order_id, 0)
    );

    SELECT axis.road_id, mowing.source_review_id
    INTO target_road_id, target_source_review_id
    FROM prepared_mowing_order mowing
    JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
    JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    WHERE mowing.id = NEW.mowing_order_id
      AND mowing.status = 'prepared'
      AND mowing.data_status = 'prepared'
      AND mowing.location_status = 'simulated'
      AND mowing.team_assignment_status = 'unassigned'
      AND mowing.equipment_assignment_status = 'unassigned'
      AND mowing.weather_check_status = 'pending'
      AND mowing.safety_check_status = 'pending'
      AND mowing.requires_operational_approval
      AND NOT mowing.authorizes_field_work
      AND NOT mowing.eligible_for_field_execution
      AND NOT mowing.eligible_for_official_reporting;

    IF NOT FOUND OR EXISTS (
        SELECT 1 FROM prepared_post_inspection_review correction
        WHERE correction.supersedes_review_id = target_source_review_id
    ) THEN
        RAISE EXCEPTION 'prepared resource plan requires a current non-executable mowing order';
    END IF;

    SELECT allowed_roles INTO policy_allowed_roles
    FROM prepared_mowing_resource_plan_policy
    WHERE id = NEW.policy_id
      AND data_status = 'prepared'
      AND NOT resource_references_are_verified
      AND requires_operational_approval
      AND NOT authorizes_field_work
      AND NOT eligible_for_field_execution;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared mowing-resource policy is unavailable';
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
        RAISE EXCEPTION 'prepared resource-plan creator lacks an eligible road role';
    END IF;

    SELECT count(*) INTO prior_count
    FROM prepared_mowing_resource_plan
    WHERE mowing_order_id = NEW.mowing_order_id;

    IF prior_count = 0 AND NEW.supersedes_plan_id IS NOT NULL THEN
        RAISE EXCEPTION 'first prepared resource plan cannot supersede another plan';
    ELSIF prior_count > 0 AND NEW.supersedes_plan_id IS NULL THEN
        RAISE EXCEPTION 'subsequent prepared resource plan must supersede the effective plan';
    ELSIF NEW.supersedes_plan_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM prepared_mowing_resource_plan prior
        WHERE prior.id = NEW.supersedes_plan_id
          AND prior.mowing_order_id = NEW.mowing_order_id
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_resource_plan newer
              WHERE newer.supersedes_plan_id = prior.id
          )
    ) THEN
        RAISE EXCEPTION 'prepared resource plan can only supersede its effective plan';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_resource_plan_guard
BEFORE INSERT ON prepared_mowing_resource_plan
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_resource_plan();

CREATE FUNCTION prevent_prepared_mowing_resource_plan_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'prepared mowing resource plans are immutable; create a correction';
END;
$$;

CREATE TRIGGER prepared_mowing_resource_plan_policy_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_resource_plan_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mowing_resource_plan_mutation();

CREATE TRIGGER prepared_mowing_resource_plan_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_resource_plan
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mowing_resource_plan_mutation();

COMMIT;
