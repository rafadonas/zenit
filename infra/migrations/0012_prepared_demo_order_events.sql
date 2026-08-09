BEGIN;

CREATE TABLE prepared_work_order_demo_event (
    event_id uuid PRIMARY KEY REFERENCES mobile_sync_event(event_id),
    work_order_id uuid NOT NULL REFERENCES work_order(id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    device_id uuid NOT NULL REFERENCES mobile_device_registration(device_id),
    operation text NOT NULL CHECK (operation IN ('confirm', 'start', 'finish')),
    client_occurred_at timestamptz NOT NULL,
    server_received_at timestamptz NOT NULL DEFAULT now(),
    location_status text NOT NULL CHECK (location_status IN ('not_collected', 'simulated')),
    simulated_location geometry(Point, 4326),
    simulation_method text,
    simulation_scope text NOT NULL CHECK (simulation_scope = 'demo_only'),
    data_status text NOT NULL DEFAULT 'simulated' CHECK (data_status = 'simulated'),
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    eligible_for_official_reporting boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_official_reporting),
    UNIQUE (work_order_id, operation),
    CHECK (
        (operation = 'start'
            AND location_status = 'simulated'
            AND simulated_location IS NOT NULL
            AND simulation_method = 'prepared_point_demo_v1')
        OR
        (operation IN ('confirm', 'finish')
            AND location_status = 'not_collected'
            AND simulated_location IS NULL
            AND simulation_method IS NULL)
    )
);

CREATE INDEX prepared_work_order_demo_event_order_idx
    ON prepared_work_order_demo_event (work_order_id, client_occurred_at);

CREATE FUNCTION validate_prepared_work_order_demo_event()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    event_payload jsonb;
BEGIN
    SELECT sync_event.payload -> 'payload'
    INTO event_payload
    FROM mobile_sync_event sync_event
    WHERE sync_event.event_id = NEW.event_id
      AND sync_event.device_id = NEW.device_id
      AND sync_event.actor_user_id = NEW.actor_user_id
      AND sync_event.outcome = 'accepted'
      AND sync_event.entity_type = 'work_order'
      AND sync_event.operation = NEW.operation;

    IF event_payload IS NULL
       OR event_payload ->> 'work_order_id' <> NEW.work_order_id::text
       OR (event_payload ->> 'occurred_at')::timestamptz <> NEW.client_occurred_at
       OR event_payload ->> 'data_status' <> 'simulated'
       OR event_payload ->> 'simulation_scope' <> 'demo_only'
       OR event_payload ->> 'location_status' <> NEW.location_status
       OR (event_payload ->> 'simulation_method') IS DISTINCT FROM NEW.simulation_method
       OR (event_payload ->> 'authorizes_field_work')::boolean <> false
       OR (event_payload ->> 'eligible_for_official_reporting')::boolean <> false
       OR (
           NEW.operation = 'start'
           AND (
               (event_payload ->> 'simulated_longitude')::double precision
                   <> ST_X(NEW.simulated_location)
               OR (event_payload ->> 'simulated_latitude')::double precision
                   <> ST_Y(NEW.simulated_location)
           )
       )
    THEN
        RAISE EXCEPTION 'demo order event requires its exact accepted sync event';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM work_order order_record
        JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN mobile_device_registration device ON device.device_id = NEW.device_id
        JOIN app_user actor ON actor.id = device.user_id
        WHERE order_record.id = NEW.work_order_id
          AND order_record.status = 'prepared'
          AND order_record.data_status = 'prepared'
          AND NOT order_record.authorizes_field_work
          AND NOT order_record.eligible_for_field_execution
          AND NOT order_record.eligible_for_official_reporting
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
        RAISE EXCEPTION 'demo order event target or actor/device authorization is invalid';
    END IF;

    IF NEW.operation = 'confirm' AND EXISTS (
        SELECT 1 FROM prepared_work_order_demo_event
        WHERE work_order_id = NEW.work_order_id
    ) THEN
        RAISE EXCEPTION 'confirm must be the first demo order event';
    ELSIF NEW.operation = 'start' AND NOT EXISTS (
        SELECT 1 FROM prepared_work_order_demo_event
        WHERE work_order_id = NEW.work_order_id AND operation = 'confirm'
    ) THEN
        RAISE EXCEPTION 'start requires a persisted confirm event';
    ELSIF NEW.operation = 'finish' AND (
        NOT EXISTS (
            SELECT 1 FROM prepared_work_order_demo_event
            WHERE work_order_id = NEW.work_order_id AND operation = 'start'
        )
        OR 3 <> (
            SELECT count(DISTINCT measurement.planned_point_id)
            FROM prepared_field_measurement measurement
            WHERE measurement.work_order_id = NEW.work_order_id
        )
    ) THEN
        RAISE EXCEPTION 'finish requires start and three prepared point measurements';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_work_order_demo_event_guard
BEFORE INSERT ON prepared_work_order_demo_event
FOR EACH ROW EXECUTE FUNCTION validate_prepared_work_order_demo_event();

CREATE TRIGGER prepared_work_order_demo_event_immutable
BEFORE UPDATE OR DELETE ON prepared_work_order_demo_event
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
