BEGIN;

CREATE TABLE prepared_inspection_summary_export_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_id uuid NOT NULL REFERENCES prepared_inspection_summary(id),
    actor_user_id uuid NOT NULL REFERENCES app_user(id),
    idempotency_key char(64) NOT NULL UNIQUE
        CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    export_schema_version text NOT NULL
        CHECK (export_schema_version = 'prepared-inspection-summary-csv-v1'),
    export_purpose text NOT NULL
        CHECK (btrim(export_purpose) <> '' AND char_length(export_purpose) <= 2000),
    checksum_sha256 char(64) NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 1048576),
    location_status text NOT NULL CHECK (location_status = 'simulated'),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    eligible_for_official_reporting boolean NOT NULL
        CHECK (NOT eligible_for_official_reporting),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    exported_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX prepared_inspection_summary_export_summary_idx
    ON prepared_inspection_summary_export_event (summary_id, exported_at DESC);
CREATE INDEX prepared_inspection_summary_export_actor_idx
    ON prepared_inspection_summary_export_event (actor_user_id, exported_at DESC);

CREATE FUNCTION validate_prepared_inspection_summary_export_event()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM prepared_inspection_summary summary
        JOIN work_order order_record ON order_record.id = summary.work_order_id
        JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN app_user actor ON actor.id = NEW.actor_user_id
        WHERE summary.id = NEW.summary_id
          AND summary.location_status = 'simulated'
          AND summary.data_status = 'prepared'
          AND NOT summary.eligible_for_official_reporting
          AND NOT summary.authorizes_field_work
          AND actor.status = 'active'
          AND EXISTS (
              SELECT 1 FROM road_user_role assignment
              WHERE assignment.user_id = actor.id
                AND assignment.road_id = axis.road_id
                AND assignment.role IN ('manager', 'supervisor')
                AND assignment.data_status <> 'simulated'
          )
    ) THEN
        RAISE EXCEPTION 'prepared summary export requires an authorized safe summary';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_inspection_summary_export_event_guard
BEFORE INSERT ON prepared_inspection_summary_export_event
FOR EACH ROW EXECUTE FUNCTION validate_prepared_inspection_summary_export_event();

CREATE TRIGGER prepared_inspection_summary_export_event_immutable
BEFORE UPDATE OR DELETE ON prepared_inspection_summary_export_event
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
