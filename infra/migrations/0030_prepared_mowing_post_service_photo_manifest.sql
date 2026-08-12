BEGIN;

CREATE TABLE prepared_mowing_post_service_photo_manifest (
    event_id uuid PRIMARY KEY REFERENCES mobile_sync_event(event_id),
    photo_id uuid NOT NULL UNIQUE,
    mowing_order_id uuid NOT NULL REFERENCES prepared_mowing_order(id),
    source_planning_approval_id uuid NOT NULL
        REFERENCES prepared_mowing_planning_approval(id),
    source_planned_point_id uuid NOT NULL REFERENCES work_order_planned_point(id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    phase text NOT NULL CHECK (phase = 'post_service'),
    client_captured_at timestamptz NOT NULL,
    checksum_sha256 char(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 26214400),
    media_type text NOT NULL CHECK (media_type IN ('image/jpeg', 'image/png')),
    photo_scope text NOT NULL CHECK (photo_scope = 'mowing_demo_post_service_only'),
    content_status text NOT NULL DEFAULT 'not_uploaded'
        CHECK (content_status = 'not_uploaded'),
    ruler_status text NOT NULL DEFAULT 'not_validated'
        CHECK (ruler_status = 'not_validated'),
    location_status text NOT NULL DEFAULT 'not_collected'
        CHECK (location_status = 'not_collected'),
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
    server_received_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT prepared_mowing_post_service_photo_point_key
        UNIQUE (mowing_order_id, source_planned_point_id)
);

CREATE INDEX prepared_mowing_post_service_photo_order_idx
    ON prepared_mowing_post_service_photo_manifest
    (mowing_order_id, client_captured_at DESC);

CREATE FUNCTION prevent_cross_scope_photo_id_reuse()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('prepared-photo:' || NEW.photo_id, 0));

    IF TG_TABLE_NAME = 'prepared_field_photo_manifest' THEN
        IF EXISTS (
            SELECT 1
            FROM prepared_mowing_post_service_photo_manifest mowing_photo
            WHERE mowing_photo.photo_id = NEW.photo_id
        ) THEN
            RAISE EXCEPTION 'photo id is already used by mowing post-service evidence';
        END IF;
    ELSIF EXISTS (
        SELECT 1
        FROM prepared_field_photo_manifest inspection_photo
        WHERE inspection_photo.photo_id = NEW.photo_id
    ) THEN
        RAISE EXCEPTION 'photo id is already used by inspection evidence';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_field_photo_manifest_cross_scope_photo_id
BEFORE INSERT ON prepared_field_photo_manifest
FOR EACH ROW EXECUTE FUNCTION prevent_cross_scope_photo_id_reuse();

CREATE TRIGGER prepared_mowing_post_service_photo_cross_scope_photo_id
BEFORE INSERT ON prepared_mowing_post_service_photo_manifest
FOR EACH ROW EXECUTE FUNCTION prevent_cross_scope_photo_id_reuse();

CREATE FUNCTION validate_prepared_mowing_post_service_photo_manifest()
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
      AND sync_event.entity_type = 'mowing_photo'
      AND sync_event.operation = 'prepare';

    IF NOT ((
        event_payload IS NOT NULL
        AND event_payload ->> 'photo_id' = NEW.photo_id::text
        AND event_payload ->> 'mowing_order_id' = NEW.mowing_order_id::text
        AND event_payload ->> 'source_planning_approval_id'
            = NEW.source_planning_approval_id::text
        AND event_payload ->> 'source_planned_point_id'
            = NEW.source_planned_point_id::text
        AND event_payload ->> 'phase' = 'post_service'
        AND (event_payload ->> 'captured_at')::timestamptz = NEW.client_captured_at
        AND event_payload ->> 'checksum_sha256' = NEW.checksum_sha256
        AND (event_payload ->> 'byte_size')::bigint = NEW.byte_size
        AND event_payload ->> 'media_type' = NEW.media_type
        AND event_payload ->> 'photo_scope' = 'mowing_demo_post_service_only'
        AND event_payload ->> 'content_status' = 'not_uploaded'
        AND event_payload ->> 'ruler_status' = 'not_validated'
        AND event_payload ->> 'location_status' = 'not_collected'
        AND event_payload ->> 'data_status' = 'simulated'
        AND event_payload ->> 'quality_status' = 'simulated_unverified'
        AND (event_payload ->> 'operational_approval_satisfied')::boolean = false
        AND (event_payload ->> 'authorizes_field_work')::boolean = false
        AND (event_payload ->> 'eligible_for_field_execution')::boolean = false
        AND (event_payload ->> 'eligible_for_model_training')::boolean = false
        AND (event_payload ->> 'eligible_for_official_reporting')::boolean = false
    ) IS TRUE) THEN
        RAISE EXCEPTION
            'prepared mowing post-service photo requires its exact accepted sync event';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM prepared_mowing_post_service_measurement measurement
        JOIN prepared_mowing_order mowing ON mowing.id = measurement.mowing_order_id
        JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
        JOIN work_order_planned_point point
          ON point.id = measurement.source_planned_point_id
         AND point.work_order_id = inspection.id
        JOIN prepared_mowing_planning_approval approval
          ON approval.id = measurement.source_planning_approval_id
        JOIN prepared_mowing_readiness_assessment assessment
          ON assessment.id = approval.readiness_assessment_id
        JOIN prepared_mowing_resource_plan plan
          ON plan.id = assessment.resource_plan_id
         AND plan.mowing_order_id = mowing.id
        JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN mobile_device_registration device ON device.device_id = NEW.device_id
        JOIN app_user actor ON actor.id = device.user_id
        WHERE measurement.mowing_order_id = NEW.mowing_order_id
          AND measurement.source_planning_approval_id = NEW.source_planning_approval_id
          AND measurement.source_planned_point_id = NEW.source_planned_point_id
          AND NEW.client_captured_at >= measurement.client_captured_at
          AND mowing.status = 'prepared'
          AND mowing.data_status = 'prepared'
          AND mowing.location_status = 'simulated'
          AND mowing.requires_operational_approval
          AND NOT mowing.authorizes_field_work
          AND NOT mowing.eligible_for_field_execution
          AND NOT mowing.eligible_for_official_reporting
          AND approval.decision = 'approved_for_planning'
          AND approval.approval_effect = 'planning_only_no_execution_authorization'
          AND NOT approval.operational_approval_satisfied
          AND NOT approval.authorizes_field_work
          AND NOT approval.eligible_for_field_execution
          AND NOT approval.eligible_for_official_reporting
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_planning_approval newer
              WHERE newer.supersedes_approval_id = approval.id)
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_readiness_assessment newer
              WHERE newer.supersedes_assessment_id = assessment.id)
          AND NOT EXISTS (
              SELECT 1 FROM prepared_mowing_resource_plan newer
              WHERE newer.supersedes_plan_id = plan.id)
          AND NOT EXISTS (
              SELECT 1 FROM prepared_post_inspection_review correction
              WHERE correction.supersedes_review_id = mowing.source_review_id)
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
            'prepared mowing post-service photo target or actor is invalid';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_post_service_photo_manifest_guard
BEFORE INSERT ON prepared_mowing_post_service_photo_manifest
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_post_service_photo_manifest();

CREATE TRIGGER prepared_mowing_post_service_photo_manifest_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_photo_manifest
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
