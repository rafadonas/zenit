BEGIN;

CREATE TABLE mobile_device_registration (
    device_id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES app_user(id),
    platform text NOT NULL CHECK (platform = 'android'),
    registered_app_version text NOT NULL CHECK (btrim(registered_app_version) <> ''),
    data_status text NOT NULL DEFAULT 'prepared' CHECK (data_status = 'prepared'),
    registration_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    registered_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(registration_metadata) = 'object')
);

CREATE INDEX mobile_device_registration_user_idx
    ON mobile_device_registration (user_id, registered_at DESC);

CREATE TABLE mobile_device_revocation (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id uuid NOT NULL UNIQUE REFERENCES mobile_device_registration(device_id),
    revoked_by_user_id uuid NOT NULL REFERENCES app_user(id),
    reason text NOT NULL CHECK (btrim(reason) <> ''),
    revoked_at timestamptz NOT NULL DEFAULT now()
);

CREATE SEQUENCE mobile_sync_cursor_seq AS bigint START WITH 1;

CREATE TABLE mobile_sync_batch (
    batch_id uuid PRIMARY KEY,
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    base_sync_cursor bigint NOT NULL CHECK (base_sync_cursor >= 0),
    sync_cursor bigint NOT NULL UNIQUE DEFAULT nextval('mobile_sync_cursor_seq'),
    request_hash char(64) NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    response_payload jsonb NOT NULL,
    data_status text NOT NULL DEFAULT 'prepared' CHECK (data_status = 'prepared'),
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    eligible_for_official_reporting boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_official_reporting),
    received_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(response_payload) = 'object'),
    CHECK ((
        response_payload ->> 'batch_id' = batch_id::text
        AND (response_payload ->> 'next_sync_cursor')::bigint = sync_cursor
        AND response_payload ->> 'data_status' = 'prepared'
        AND (response_payload ->> 'authorizes_field_work')::boolean = false
        AND (response_payload ->> 'eligible_for_official_reporting')::boolean = false
    ) IS TRUE)
);

CREATE INDEX mobile_sync_batch_device_idx
    ON mobile_sync_batch (device_id, sync_cursor DESC);

CREATE TABLE mobile_sync_event (
    event_id uuid PRIMARY KEY,
    first_batch_id uuid NOT NULL REFERENCES mobile_sync_batch(batch_id)
        DEFERRABLE INITIALLY DEFERRED,
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    entity_type text NOT NULL CHECK (entity_type ~ '^[a-z_]+$'),
    operation text NOT NULL CHECK (operation ~ '^[a-z_]+$'),
    request_hash char(64) NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    payload jsonb NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('accepted', 'rejected')),
    result_code text NOT NULL CHECK (btrim(result_code) <> ''),
    result_message text NOT NULL CHECK (btrim(result_message) <> ''),
    data_status text NOT NULL DEFAULT 'prepared' CHECK (data_status = 'prepared'),
    received_at timestamptz NOT NULL DEFAULT now(),
    CHECK (jsonb_typeof(payload) = 'object'),
    CHECK ((
        payload ->> 'event_id' = event_id::text
        AND payload ->> 'entity_type' = entity_type
        AND payload ->> 'operation' = operation
        AND jsonb_typeof(payload -> 'payload') = 'object'
    ) IS TRUE)
);

CREATE INDEX mobile_sync_event_batch_idx ON mobile_sync_event (first_batch_id);

CREATE TABLE mobile_sync_conflict (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id uuid NOT NULL REFERENCES mobile_sync_batch(batch_id)
        DEFERRABLE INITIALLY DEFERRED,
    event_id uuid NOT NULL REFERENCES mobile_sync_event(event_id),
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    persisted_request_hash char(64) NOT NULL
        CHECK (persisted_request_hash ~ '^[0-9a-f]{64}$'),
    incoming_request_hash char(64) NOT NULL
        CHECK (incoming_request_hash ~ '^[0-9a-f]{64}$'),
    persisted_payload jsonb NOT NULL,
    incoming_payload jsonb NOT NULL,
    conflict_code text NOT NULL CHECK (btrim(conflict_code) <> ''),
    data_status text NOT NULL DEFAULT 'prepared' CHECK (data_status = 'prepared'),
    detected_at timestamptz NOT NULL DEFAULT now(),
    CHECK (persisted_request_hash <> incoming_request_hash),
    CHECK (jsonb_typeof(persisted_payload) = 'object'),
    CHECK (jsonb_typeof(incoming_payload) = 'object')
);

CREATE INDEX mobile_sync_conflict_event_idx
    ON mobile_sync_conflict (event_id, detected_at DESC);

CREATE TABLE prepared_field_measurement (
    event_id uuid PRIMARY KEY REFERENCES mobile_sync_event(event_id),
    work_order_id uuid NOT NULL REFERENCES work_order(id),
    planned_point_id uuid NOT NULL REFERENCES work_order_planned_point(id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    phase text NOT NULL CHECK (phase = 'inspection'),
    height_cm numeric(7, 2) NOT NULL CHECK (height_cm >= 0 AND height_cm <= 1000),
    client_captured_at timestamptz NOT NULL,
    server_received_at timestamptz NOT NULL DEFAULT now(),
    quality_status text NOT NULL DEFAULT 'prepared_unverified'
        CHECK (quality_status = 'prepared_unverified'),
    data_status text NOT NULL DEFAULT 'prepared' CHECK (data_status = 'prepared'),
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    eligible_for_official_reporting boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_official_reporting),
    measurement_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    CHECK (jsonb_typeof(measurement_metadata) = 'object')
);

CREATE INDEX prepared_field_measurement_order_idx
    ON prepared_field_measurement (work_order_id, client_captured_at DESC);
CREATE INDEX prepared_field_measurement_point_idx
    ON prepared_field_measurement (planned_point_id, client_captured_at DESC);

CREATE FUNCTION validate_mobile_device_registration()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM app_user actor
        WHERE actor.id = NEW.user_id AND actor.status = 'active'
    ) THEN
        RAISE EXCEPTION 'mobile device registration requires an active user';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER mobile_device_registration_guard
BEFORE INSERT ON mobile_device_registration
FOR EACH ROW EXECUTE FUNCTION validate_mobile_device_registration();

CREATE FUNCTION validate_mobile_sync_batch()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM mobile_device_registration device
        JOIN app_user actor ON actor.id = device.user_id
        WHERE device.device_id = NEW.device_id
          AND device.user_id = NEW.actor_user_id
          AND actor.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM mobile_device_revocation revocation
              WHERE revocation.device_id = device.device_id
          )
    ) THEN
        RAISE EXCEPTION 'mobile sync requires an active device owned by the actor';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER mobile_sync_batch_guard
BEFORE INSERT ON mobile_sync_batch
FOR EACH ROW EXECUTE FUNCTION validate_mobile_sync_batch();

CREATE FUNCTION validate_prepared_field_measurement()
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
              SELECT 1
              FROM road_user_role assignment
              WHERE assignment.user_id = NEW.actor_user_id
                AND assignment.road_id = axis.road_id
                AND assignment.role IN ('manager', 'supervisor')
                AND assignment.data_status <> 'simulated'
          )
    ) THEN
        RAISE EXCEPTION 'prepared measurement target or actor/device authorization is invalid';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM mobile_sync_event event_record
        WHERE event_record.event_id = NEW.event_id
          AND event_record.device_id = NEW.device_id
          AND event_record.actor_user_id = NEW.actor_user_id
          AND event_record.outcome = 'accepted'
          AND event_record.entity_type = 'measurement'
          AND event_record.operation = 'create'
          AND event_record.payload -> 'payload' ->> 'work_order_id' = NEW.work_order_id::text
          AND event_record.payload -> 'payload' ->> 'planned_point_id' = NEW.planned_point_id::text
          AND event_record.payload -> 'payload' ->> 'phase' = NEW.phase
          AND (event_record.payload -> 'payload' ->> 'height_cm')::numeric = NEW.height_cm
          AND (event_record.payload -> 'payload' ->> 'captured_at')::timestamptz
              = NEW.client_captured_at
          AND event_record.payload -> 'payload' ->> 'data_status' = 'prepared'
          AND (event_record.payload -> 'payload' ->> 'eligible_for_official_reporting')::boolean
              = false
    ) THEN
        RAISE EXCEPTION 'prepared measurement requires its accepted sync event';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_field_measurement_guard
BEFORE INSERT ON prepared_field_measurement
FOR EACH ROW EXECUTE FUNCTION validate_prepared_field_measurement();

CREATE FUNCTION prevent_prepared_mobile_sync_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'prepared mobile sync records are append-only';
END;
$$;

CREATE TRIGGER mobile_device_registration_immutable
BEFORE UPDATE OR DELETE ON mobile_device_registration
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

CREATE TRIGGER mobile_device_revocation_immutable
BEFORE UPDATE OR DELETE ON mobile_device_revocation
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

CREATE TRIGGER mobile_sync_batch_immutable
BEFORE UPDATE OR DELETE ON mobile_sync_batch
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

CREATE TRIGGER mobile_sync_event_immutable
BEFORE UPDATE OR DELETE ON mobile_sync_event
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

CREATE TRIGGER mobile_sync_conflict_immutable
BEFORE UPDATE OR DELETE ON mobile_sync_conflict
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

CREATE TRIGGER prepared_field_measurement_immutable
BEFORE UPDATE OR DELETE ON prepared_field_measurement
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
