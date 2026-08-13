BEGIN;

CREATE TABLE prepared_mowing_post_service_exception_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL
        CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    general_threshold_cm numeric(7,2) NOT NULL CHECK (general_threshold_cm = 30),
    special_threshold_cm numeric(7,2) NOT NULL CHECK (special_threshold_cm = 10),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    requires_human_review boolean NOT NULL CHECK (requires_human_review),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    policy_metadata jsonb NOT NULL CHECK (jsonb_typeof(policy_metadata) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(allowed_roles) > 0)
);

INSERT INTO prepared_mowing_post_service_exception_policy (
    id, version, allowed_roles, general_threshold_cm, special_threshold_cm,
    data_status, requires_human_review, eligible_for_official_reporting,
    authorizes_field_work, policy_metadata
) VALUES (
    '90000000-0000-4000-8000-000000000009',
    'prepared-mowing-post-service-exception-v1', ARRAY['manager', 'supervisor'],
    30, 10, 'prepared', true, false, false,
    '{"official_motiva_policy":false,"scope":"simulated_post_service_exception_only"}'::jsonb
);

CREATE TABLE prepared_mowing_post_service_exception (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_id uuid NOT NULL UNIQUE REFERENCES prepared_mowing_post_service_summary(id),
    created_by_user_id uuid NOT NULL REFERENCES app_user(id),
    policy_id uuid NOT NULL REFERENCES prepared_mowing_post_service_exception_policy(id),
    idempotency_key char(64) NOT NULL UNIQUE CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    creation_rationale text NOT NULL CHECK (btrim(creation_rationale) <> ''),
    recommendation text NOT NULL CHECK (recommendation IN ('monitor', 'inspect_follow_up')),
    applicable_threshold_cm numeric(7,2) NOT NULL CHECK (applicable_threshold_cm IN (10, 30)),
    maximum_height_cm numeric(7,2) NOT NULL CHECK (maximum_height_cm >= 0),
    threshold_exceeded boolean NOT NULL,
    requires_human_review boolean NOT NULL CHECK (requires_human_review),
    phase text NOT NULL CHECK (phase = 'post_service'),
    data_status text NOT NULL CHECK (data_status = 'simulated'),
    location_status text NOT NULL CHECK (location_status = 'not_collected'),
    evidence_status text NOT NULL CHECK (evidence_status = 'simulated_reviewed_non_operational'),
    eligible_for_model_training boolean NOT NULL CHECK (NOT eligible_for_model_training),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (threshold_exceeded = (maximum_height_cm > applicable_threshold_cm)),
    CHECK ((recommendation = 'inspect_follow_up') = threshold_exceeded)
);

CREATE FUNCTION validate_prepared_mowing_post_service_exception()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected record;
BEGIN
    SELECT summary.maximum_height_cm,
           CASE WHEN zone.zone_type = 'special'
                THEN policy.special_threshold_cm ELSE policy.general_threshold_cm END AS threshold_cm
    INTO expected
    FROM prepared_mowing_post_service_summary summary
    JOIN prepared_mowing_order mowing ON mowing.id = summary.mowing_order_id
    JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
    JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    JOIN prepared_mowing_post_service_exception_policy policy ON policy.id = NEW.policy_id
    JOIN app_user actor ON actor.id = NEW.created_by_user_id
    WHERE summary.id = NEW.summary_id
      AND summary.phase = 'post_service'
      AND summary.data_status = 'simulated'
      AND summary.location_status = 'not_collected'
      AND NOT summary.eligible_for_official_reporting
      AND NOT summary.authorizes_field_work
      AND policy.data_status = 'prepared'
      AND policy.requires_human_review
      AND NOT policy.eligible_for_official_reporting
      AND NOT policy.authorizes_field_work
      AND actor.status = 'active'
      AND EXISTS (
          SELECT 1 FROM road_user_role assignment
          WHERE assignment.user_id = actor.id
            AND assignment.road_id = axis.road_id
            AND assignment.role = ANY(policy.allowed_roles)
            AND assignment.data_status <> 'simulated'
      );

    IF expected IS NULL OR
       (NEW.maximum_height_cm, NEW.applicable_threshold_cm, NEW.threshold_exceeded,
        NEW.recommendation) IS DISTINCT FROM
       (expected.maximum_height_cm, expected.threshold_cm,
        expected.maximum_height_cm > expected.threshold_cm,
        CASE WHEN expected.maximum_height_cm > expected.threshold_cm
             THEN 'inspect_follow_up' ELSE 'monitor' END)
    THEN
        RAISE EXCEPTION 'post-service exception requires exact simulated summary threshold rule';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_post_service_exception_guard
BEFORE INSERT ON prepared_mowing_post_service_exception
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_post_service_exception();
CREATE TRIGGER prepared_mowing_post_service_exception_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_exception
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();
CREATE TRIGGER prepared_mowing_post_service_exception_policy_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_exception_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
