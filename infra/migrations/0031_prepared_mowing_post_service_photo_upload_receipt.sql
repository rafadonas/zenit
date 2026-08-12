BEGIN;

CREATE TABLE prepared_mowing_post_service_photo_upload_receipt (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id uuid NOT NULL UNIQUE
        REFERENCES prepared_mowing_post_service_photo_manifest(photo_id),
    manifest_event_id uuid NOT NULL UNIQUE
        REFERENCES prepared_mowing_post_service_photo_manifest(event_id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    object_bucket text NOT NULL CHECK (btrim(object_bucket) <> ''),
    object_name text NOT NULL UNIQUE
        CHECK (object_name LIKE 'simulated-mowing-post-service-photos/%'),
    object_version_id text NOT NULL CHECK (btrim(object_version_id) <> ''),
    object_etag text NOT NULL CHECK (btrim(object_etag) <> ''),
    checksum_sha256 char(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 26214400),
    media_type text NOT NULL CHECK (media_type IN ('image/jpeg', 'image/png')),
    encryption_method text NOT NULL CHECK (encryption_method = 'APP-AES256-GCM'),
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
    uploaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE FUNCTION validate_prepared_mowing_post_service_photo_upload_receipt()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM prepared_mowing_post_service_photo_manifest manifest
        WHERE manifest.photo_id = NEW.photo_id
          AND manifest.event_id = NEW.manifest_event_id
          AND manifest.actor_user_id = NEW.actor_user_id
          AND manifest.device_id = NEW.device_id
          AND manifest.checksum_sha256 = NEW.checksum_sha256
          AND manifest.byte_size = NEW.byte_size
          AND manifest.media_type = NEW.media_type
          AND manifest.phase = NEW.phase
          AND manifest.photo_scope = NEW.photo_scope
          AND manifest.content_status = 'not_uploaded'
          AND NEW.content_status = 'uploaded_unverified'
          AND manifest.ruler_status = NEW.ruler_status
          AND manifest.location_status = NEW.location_status
          AND manifest.quality_status = NEW.quality_status
          AND manifest.data_status = NEW.data_status
          AND manifest.operational_approval_satisfied
              = NEW.operational_approval_satisfied
          AND manifest.authorizes_field_work = NEW.authorizes_field_work
          AND manifest.eligible_for_field_execution
              = NEW.eligible_for_field_execution
          AND manifest.eligible_for_model_training
              = NEW.eligible_for_model_training
          AND manifest.eligible_for_official_reporting
              = NEW.eligible_for_official_reporting
    ) THEN
        RAISE EXCEPTION
            'mowing post-service upload receipt requires its exact simulated manifest';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_post_service_photo_upload_receipt_guard
BEFORE INSERT ON prepared_mowing_post_service_photo_upload_receipt
FOR EACH ROW
EXECUTE FUNCTION validate_prepared_mowing_post_service_photo_upload_receipt();

CREATE TRIGGER prepared_mowing_post_service_photo_upload_receipt_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_photo_upload_receipt
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
