BEGIN;

CREATE TABLE prepared_photo_upload_receipt (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id uuid NOT NULL UNIQUE REFERENCES prepared_field_photo_manifest(photo_id),
    manifest_event_id uuid NOT NULL UNIQUE REFERENCES prepared_field_photo_manifest(event_id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    object_bucket text NOT NULL CHECK (btrim(object_bucket) <> ''),
    object_name text NOT NULL UNIQUE CHECK (btrim(object_name) <> ''),
    object_version_id text NOT NULL CHECK (btrim(object_version_id) <> ''),
    object_etag text NOT NULL CHECK (btrim(object_etag) <> ''),
    checksum_sha256 char(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 26214400),
    media_type text NOT NULL CHECK (media_type IN ('image/jpeg', 'image/png')),
    encryption_method text NOT NULL CHECK (encryption_method = 'APP-AES256-GCM'),
    content_status text NOT NULL CHECK (content_status = 'uploaded_unverified'),
    ruler_status text NOT NULL CHECK (ruler_status = 'not_validated'),
    quality_status text NOT NULL CHECK (quality_status = 'prepared_unverified'),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    uploaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE FUNCTION validate_prepared_photo_upload_receipt()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM prepared_field_photo_manifest manifest
        WHERE manifest.photo_id = NEW.photo_id
          AND manifest.event_id = NEW.manifest_event_id
          AND manifest.actor_user_id = NEW.actor_user_id
          AND manifest.device_id = NEW.device_id
          AND manifest.checksum_sha256 = NEW.checksum_sha256
          AND manifest.byte_size = NEW.byte_size
          AND manifest.media_type = NEW.media_type
          AND manifest.content_status = 'not_uploaded'
          AND manifest.ruler_status = 'not_validated'
          AND manifest.quality_status = 'prepared_unverified'
          AND manifest.data_status = 'prepared'
          AND NOT manifest.eligible_for_official_reporting
    ) THEN
        RAISE EXCEPTION 'photo upload receipt requires its exact prepared manifest';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_photo_upload_receipt_guard
BEFORE INSERT ON prepared_photo_upload_receipt
FOR EACH ROW EXECUTE FUNCTION validate_prepared_photo_upload_receipt();

CREATE TRIGGER prepared_photo_upload_receipt_immutable
BEFORE UPDATE OR DELETE ON prepared_photo_upload_receipt
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
