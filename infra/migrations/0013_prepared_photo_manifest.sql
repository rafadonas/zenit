BEGIN;

CREATE TABLE prepared_field_photo_manifest (
    event_id uuid PRIMARY KEY REFERENCES mobile_sync_event(event_id),
    photo_id uuid NOT NULL UNIQUE,
    work_order_id uuid NOT NULL REFERENCES work_order(id),
    planned_point_id uuid NOT NULL REFERENCES work_order_planned_point(id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    phase text NOT NULL CHECK (phase = 'inspection'),
    client_captured_at timestamptz NOT NULL,
    checksum_sha256 char(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 26214400),
    media_type text NOT NULL CHECK (media_type IN ('image/jpeg', 'image/png')),
    content_status text NOT NULL DEFAULT 'not_uploaded'
        CHECK (content_status = 'not_uploaded'),
    ruler_status text NOT NULL DEFAULT 'not_validated'
        CHECK (ruler_status = 'not_validated'),
    quality_status text NOT NULL DEFAULT 'prepared_unverified'
        CHECK (quality_status = 'prepared_unverified'),
    location_status text NOT NULL DEFAULT 'not_collected'
        CHECK (location_status = 'not_collected'),
    data_status text NOT NULL DEFAULT 'prepared' CHECK (data_status = 'prepared'),
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    eligible_for_official_reporting boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_official_reporting),
    server_received_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX prepared_field_photo_manifest_order_idx
    ON prepared_field_photo_manifest (work_order_id, client_captured_at DESC);
CREATE INDEX prepared_field_photo_manifest_point_idx
    ON prepared_field_photo_manifest (planned_point_id, client_captured_at DESC);

CREATE FUNCTION validate_prepared_field_photo_manifest()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM work_order_planned_point point
        JOIN work_order order_record ON order_record.id = point.work_order_id
        JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN mobile_device_registration device ON device.device_id = NEW.device_id
        JOIN app_user actor ON actor.id = device.user_id
        WHERE point.id = NEW.planned_point_id
          AND point.work_order_id = NEW.work_order_id
          AND order_record.status = 'prepared'
          AND order_record.data_status = 'prepared'
          AND NOT order_record.authorizes_field_work
          AND NOT order_record.eligible_for_field_execution
          AND NOT order_record.eligible_for_official_reporting
          AND NOT point.eligible_for_field_execution
          AND device.user_id = NEW.actor_user_id
          AND actor.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM mobile_device_revocation revocation
              WHERE revocation.device_id = device.device_id
          )
          AND EXISTS (
              SELECT 1 FROM road_user_role assignment
              WHERE assignment.user_id = NEW.actor_user_id
                AND assignment.road_id = axis.road_id
                AND assignment.role IN ('manager', 'supervisor')
                AND assignment.data_status <> 'simulated'
          )
    ) THEN
        RAISE EXCEPTION 'prepared photo target or actor/device authorization is invalid';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM mobile_sync_event sync_event
        WHERE sync_event.event_id = NEW.event_id
          AND sync_event.device_id = NEW.device_id
          AND sync_event.actor_user_id = NEW.actor_user_id
          AND sync_event.outcome = 'accepted'
          AND sync_event.entity_type = 'photo'
          AND sync_event.operation = 'prepare'
          AND sync_event.payload -> 'payload' ->> 'photo_id' = NEW.photo_id::text
          AND sync_event.payload -> 'payload' ->> 'work_order_id' = NEW.work_order_id::text
          AND sync_event.payload -> 'payload' ->> 'planned_point_id'
              = NEW.planned_point_id::text
          AND sync_event.payload -> 'payload' ->> 'phase' = NEW.phase
          AND (sync_event.payload -> 'payload' ->> 'captured_at')::timestamptz
              = NEW.client_captured_at
          AND sync_event.payload -> 'payload' ->> 'checksum_sha256'
              = NEW.checksum_sha256
          AND (sync_event.payload -> 'payload' ->> 'byte_size')::bigint = NEW.byte_size
          AND sync_event.payload -> 'payload' ->> 'media_type' = NEW.media_type
          AND sync_event.payload -> 'payload' ->> 'content_status' = 'not_uploaded'
          AND sync_event.payload -> 'payload' ->> 'ruler_status' = 'not_validated'
          AND sync_event.payload -> 'payload' ->> 'location_status' = 'not_collected'
          AND sync_event.payload -> 'payload' ->> 'data_status' = 'prepared'
          AND (sync_event.payload -> 'payload' ->> 'eligible_for_official_reporting')::boolean
              = false
    ) THEN
        RAISE EXCEPTION 'prepared photo manifest requires its exact accepted sync event';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_field_photo_manifest_guard
BEFORE INSERT ON prepared_field_photo_manifest
FOR EACH ROW EXECUTE FUNCTION validate_prepared_field_photo_manifest();

CREATE TRIGGER prepared_field_photo_manifest_immutable
BEFORE UPDATE OR DELETE ON prepared_field_photo_manifest
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
