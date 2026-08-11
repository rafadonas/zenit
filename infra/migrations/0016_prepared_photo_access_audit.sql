BEGIN;

CREATE TABLE prepared_photo_access_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id uuid NOT NULL REFERENCES prepared_photo_upload_receipt(photo_id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    access_purpose text NOT NULL CHECK (access_purpose = 'human_review'),
    source_channel text NOT NULL CHECK (source_channel = 'api'),
    checksum_sha256 char(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 26214400),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    eligible_for_official_reporting boolean NOT NULL
        CHECK (NOT eligible_for_official_reporting),
    accessed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX prepared_photo_access_event_photo_idx
    ON prepared_photo_access_event (photo_id, accessed_at DESC);
CREATE INDEX prepared_photo_access_event_actor_idx
    ON prepared_photo_access_event (actor_user_id, accessed_at DESC);

CREATE FUNCTION validate_prepared_photo_access_event()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM prepared_photo_upload_receipt receipt
        JOIN prepared_field_photo_manifest manifest
          ON manifest.photo_id = receipt.photo_id
        JOIN work_order order_record ON order_record.id = manifest.work_order_id
        JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis
          ON axis.id = segment.road_axis_candidate_id
        JOIN app_user actor ON actor.id = NEW.actor_user_id
        WHERE receipt.photo_id = NEW.photo_id
          AND receipt.checksum_sha256 = NEW.checksum_sha256
          AND receipt.byte_size = NEW.byte_size
          AND receipt.content_status = 'uploaded_unverified'
          AND receipt.ruler_status = 'not_validated'
          AND receipt.quality_status = 'prepared_unverified'
          AND receipt.data_status = 'prepared'
          AND NOT receipt.eligible_for_official_reporting
          AND actor.status = 'active'
          AND EXISTS (
              SELECT 1 FROM road_user_role assignment
              WHERE assignment.user_id = actor.id
                AND assignment.road_id = axis.road_id
                AND assignment.role IN ('manager', 'supervisor')
                AND assignment.data_status <> 'simulated'
          )
    ) THEN
        RAISE EXCEPTION 'prepared photo access requires an authorized exact receipt';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_photo_access_event_guard
BEFORE INSERT ON prepared_photo_access_event
FOR EACH ROW EXECUTE FUNCTION validate_prepared_photo_access_event();

CREATE TRIGGER prepared_photo_access_event_immutable
BEFORE UPDATE OR DELETE ON prepared_photo_access_event
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
