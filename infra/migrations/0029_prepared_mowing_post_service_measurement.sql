BEGIN;

CREATE TABLE prepared_mowing_post_service_measurement (
    event_id uuid PRIMARY KEY REFERENCES mobile_sync_event(event_id),
    measurement_sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    mowing_order_id uuid NOT NULL REFERENCES prepared_mowing_order(id),
    source_planning_approval_id uuid NOT NULL
        REFERENCES prepared_mowing_planning_approval(id),
    source_planned_point_id uuid NOT NULL REFERENCES work_order_planned_point(id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    phase text NOT NULL CHECK (phase = 'post_service'),
    height_cm numeric(7, 2) NOT NULL CHECK (height_cm >= 0 AND height_cm <= 1000),
    client_captured_at timestamptz NOT NULL,
    server_received_at timestamptz NOT NULL DEFAULT now(),
    measurement_scope text NOT NULL
        CHECK (measurement_scope = 'mowing_demo_post_service_only'),
    location_status text NOT NULL CHECK (location_status = 'not_collected'),
    photo_status text NOT NULL CHECK (photo_status = 'not_collected'),
    data_status text NOT NULL DEFAULT 'simulated' CHECK (data_status = 'simulated'),
    quality_status text NOT NULL DEFAULT 'simulated_unverified'
        CHECK (quality_status = 'simulated_unverified'),
    operational_approval_satisfied boolean NOT NULL DEFAULT false
        CHECK (NOT operational_approval_satisfied),
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_field_execution),
    eligible_for_model_training boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_model_training),
    eligible_for_official_reporting boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_official_reporting),
    CONSTRAINT prepared_mowing_post_service_measurement_point_key
        UNIQUE (mowing_order_id, source_planned_point_id)
);

CREATE INDEX prepared_mowing_post_service_measurement_order_idx
    ON prepared_mowing_post_service_measurement
    (mowing_order_id, measurement_sequence);

CREATE FUNCTION validate_prepared_mowing_post_service_measurement()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    event_payload jsonb;
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-mowing-demo:' || NEW.mowing_order_id, 0)
    );

    SELECT sync_event.payload -> 'payload'
    INTO event_payload
    FROM mobile_sync_event sync_event
    WHERE sync_event.event_id = NEW.event_id
      AND sync_event.device_id = NEW.device_id
      AND sync_event.actor_user_id = NEW.actor_user_id
      AND sync_event.outcome = 'accepted'
      AND sync_event.entity_type = 'mowing_measurement'
      AND sync_event.operation = 'create';

    IF NOT ((
        event_payload IS NOT NULL
        AND event_payload ->> 'mowing_order_id' = NEW.mowing_order_id::text
        AND event_payload ->> 'source_planning_approval_id'
            = NEW.source_planning_approval_id::text
        AND event_payload ->> 'source_planned_point_id'
            = NEW.source_planned_point_id::text
        AND event_payload ->> 'phase' = NEW.phase
        AND (event_payload ->> 'height_cm')::numeric = NEW.height_cm
        AND (event_payload ->> 'captured_at')::timestamptz = NEW.client_captured_at
        AND event_payload ->> 'measurement_scope' = NEW.measurement_scope
        AND event_payload ->> 'location_status' = NEW.location_status
        AND event_payload ->> 'photo_status' = NEW.photo_status
        AND event_payload ->> 'data_status' = 'simulated'
        AND event_payload ->> 'quality_status' = 'simulated_unverified'
        AND (event_payload ->> 'operational_approval_satisfied')::boolean = false
        AND (event_payload ->> 'authorizes_field_work')::boolean = false
        AND (event_payload ->> 'eligible_for_field_execution')::boolean = false
        AND (event_payload ->> 'eligible_for_model_training')::boolean = false
        AND (event_payload ->> 'eligible_for_official_reporting')::boolean = false
    ) IS TRUE) THEN
        RAISE EXCEPTION
            'prepared mowing post-service measurement requires its exact accepted sync event';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM prepared_mowing_order mowing
        JOIN work_order inspection
          ON inspection.id = mowing.source_inspection_work_order_id
        JOIN work_order_planned_point point
          ON point.id = NEW.source_planned_point_id
         AND point.work_order_id = inspection.id
        JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN prepared_mowing_resource_plan plan ON plan.mowing_order_id = mowing.id
        JOIN prepared_mowing_readiness_assessment assessment
          ON assessment.resource_plan_id = plan.id
        JOIN prepared_mowing_planning_approval approval
          ON approval.readiness_assessment_id = assessment.id
        JOIN prepared_mowing_demo_event finish_event
          ON finish_event.mowing_order_id = mowing.id
         AND finish_event.operation = 'finish'
        JOIN mobile_device_registration device ON device.device_id = NEW.device_id
        JOIN app_user actor ON actor.id = device.user_id
        WHERE mowing.id = NEW.mowing_order_id
          AND approval.id = NEW.source_planning_approval_id
          AND approval.mowing_order_id = mowing.id
          AND finish_event.source_planning_approval_id = approval.id
          AND NEW.client_captured_at >= finish_event.client_occurred_at
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
          AND NOT mowing.eligible_for_official_reporting
          AND NOT point.eligible_for_field_execution
          AND plan.resource_reference_status
              = 'prepared_placeholder_pending_validation'
          AND plan.team_assignment_status = 'unassigned'
          AND plan.equipment_assignment_status = 'unassigned'
          AND plan.requires_operational_approval
          AND NOT plan.authorizes_field_work
          AND NOT plan.eligible_for_field_execution
          AND NOT plan.eligible_for_official_reporting
          AND assessment.weather_result = 'clear'
          AND assessment.safety_result = 'clear'
          AND assessment.validation_status = 'prepared_manual_pending_validation'
          AND assessment.requires_operational_approval
          AND NOT assessment.authorizes_field_work
          AND NOT assessment.eligible_for_field_execution
          AND NOT assessment.eligible_for_official_reporting
          AND approval.decision = 'approved_for_planning'
          AND approval.approval_effect = 'planning_only_no_execution_authorization'
          AND approval.dual_approval_requirement_status
              = 'pending_official_policy_validation'
          AND NOT approval.operational_approval_satisfied
          AND NOT approval.authorizes_field_work
          AND NOT approval.eligible_for_field_execution
          AND NOT approval.eligible_for_official_reporting
          AND NOT EXISTS (
              SELECT 1 FROM prepared_post_inspection_review correction
              WHERE correction.supersedes_review_id = mowing.source_review_id)
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_resource_plan newer_plan
              WHERE newer_plan.supersedes_plan_id = plan.id)
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_readiness_assessment newer_assessment
              WHERE newer_assessment.supersedes_assessment_id = assessment.id)
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_planning_approval newer_approval
              WHERE newer_approval.supersedes_approval_id = approval.id)
          AND device.user_id = NEW.actor_user_id
          AND actor.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM mobile_device_revocation revocation
              WHERE revocation.device_id = device.device_id)
          AND EXISTS (
              SELECT 1 FROM road_user_role assignment
              WHERE assignment.user_id = NEW.actor_user_id
                AND assignment.road_id = axis.road_id
                AND assignment.role IN ('manager', 'supervisor')
                AND assignment.data_status <> 'simulated')
    ) THEN
        RAISE EXCEPTION
            'prepared mowing post-service measurement target or actor is invalid';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_post_service_measurement_guard
BEFORE INSERT ON prepared_mowing_post_service_measurement
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_post_service_measurement();

CREATE TRIGGER prepared_mowing_post_service_measurement_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_measurement
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
