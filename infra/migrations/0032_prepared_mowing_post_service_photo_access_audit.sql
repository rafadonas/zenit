BEGIN;

CREATE TABLE prepared_mowing_post_service_photo_access_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id uuid NOT NULL
        REFERENCES prepared_mowing_post_service_photo_upload_receipt(photo_id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    access_purpose text NOT NULL CHECK (access_purpose = 'human_review'),
    source_channel text NOT NULL CHECK (source_channel = 'api'),
    checksum_sha256 char(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 26214400),
    phase text NOT NULL DEFAULT 'post_service' CHECK (phase = 'post_service'),
    photo_scope text NOT NULL DEFAULT 'mowing_demo_post_service_only'
        CHECK (photo_scope = 'mowing_demo_post_service_only'),
    content_status text NOT NULL DEFAULT 'uploaded_unverified'
        CHECK (content_status = 'uploaded_unverified'),
    ruler_status text NOT NULL DEFAULT 'not_validated'
        CHECK (ruler_status = 'not_validated'),
    location_status text NOT NULL DEFAULT 'not_collected'
        CHECK (location_status = 'not_collected'),
    quality_status text NOT NULL DEFAULT 'simulated_unverified'
        CHECK (quality_status = 'simulated_unverified'),
    data_status text NOT NULL DEFAULT 'simulated' CHECK (data_status = 'simulated'),
    operational_approval_satisfied boolean NOT NULL DEFAULT false
        CHECK (NOT operational_approval_satisfied),
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_field_execution),
    eligible_for_model_training boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_model_training),
    eligible_for_official_reporting boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_official_reporting),
    accessed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX prepared_mowing_post_service_photo_access_photo_idx
    ON prepared_mowing_post_service_photo_access_event (photo_id, accessed_at DESC);
CREATE INDEX prepared_mowing_post_service_photo_access_actor_idx
    ON prepared_mowing_post_service_photo_access_event (actor_user_id, accessed_at DESC);

CREATE FUNCTION validate_prepared_mowing_post_service_photo_access_event()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM prepared_mowing_post_service_photo_upload_receipt receipt
        JOIN prepared_mowing_post_service_photo_manifest manifest
          ON manifest.photo_id = receipt.photo_id
        JOIN prepared_mowing_order mowing ON mowing.id = manifest.mowing_order_id
        JOIN work_order inspection
          ON inspection.id = mowing.source_inspection_work_order_id
        JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN app_user actor ON actor.id = NEW.actor_user_id
        WHERE receipt.photo_id = NEW.photo_id
          AND receipt.checksum_sha256 = NEW.checksum_sha256
          AND receipt.byte_size = NEW.byte_size
          AND receipt.phase = NEW.phase
          AND receipt.photo_scope = NEW.photo_scope
          AND receipt.content_status = NEW.content_status
          AND receipt.ruler_status = NEW.ruler_status
          AND receipt.location_status = NEW.location_status
          AND receipt.quality_status = NEW.quality_status
          AND receipt.data_status = NEW.data_status
          AND receipt.operational_approval_satisfied
              = NEW.operational_approval_satisfied
          AND receipt.authorizes_field_work = NEW.authorizes_field_work
          AND receipt.eligible_for_field_execution
              = NEW.eligible_for_field_execution
          AND receipt.eligible_for_model_training
              = NEW.eligible_for_model_training
          AND receipt.eligible_for_official_reporting
              = NEW.eligible_for_official_reporting
          AND actor.status = 'active'
          AND EXISTS (
              SELECT 1 FROM road_user_role assignment
              WHERE assignment.user_id = actor.id
                AND assignment.road_id = axis.road_id
                AND assignment.role IN ('manager', 'supervisor')
                AND assignment.data_status <> 'simulated'
          )
    ) THEN
        RAISE EXCEPTION
            'simulated mowing photo access requires an authorized exact receipt';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_post_service_photo_access_event_guard
BEFORE INSERT ON prepared_mowing_post_service_photo_access_event
FOR EACH ROW
EXECUTE FUNCTION validate_prepared_mowing_post_service_photo_access_event();

CREATE TRIGGER prepared_mowing_post_service_photo_access_event_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_photo_access_event
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
