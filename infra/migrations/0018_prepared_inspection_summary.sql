BEGIN;

CREATE TABLE prepared_inspection_summary_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    n1_upper_exclusive_cm numeric(7,2) NOT NULL CHECK (n1_upper_exclusive_cm = 10),
    n2_upper_inclusive_cm numeric(7,2) NOT NULL CHECK (n2_upper_inclusive_cm = 30),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    policy_metadata jsonb NOT NULL CHECK (jsonb_typeof(policy_metadata) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO prepared_inspection_summary_policy (
    id, version, allowed_roles, n1_upper_exclusive_cm, n2_upper_inclusive_cm,
    data_status, authorizes_field_work, policy_metadata
) VALUES (
    '90000000-0000-4000-8000-000000000005',
    'prepared-inspection-summary-v1', ARRAY['manager', 'supervisor'],
    10, 30, 'prepared', false,
    '{"class_rule":"N1 < 10; N2 10-30; N3 > 30","official_report":false}'::jsonb
);

CREATE TABLE prepared_inspection_summary (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id uuid NOT NULL UNIQUE REFERENCES work_order(id),
    generated_by_user_id uuid NOT NULL REFERENCES app_user(id),
    summary_policy_id uuid NOT NULL REFERENCES prepared_inspection_summary_policy(id),
    idempotency_key char(64) NOT NULL UNIQUE CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    generation_rationale text NOT NULL CHECK (btrim(generation_rationale) <> ''),
    measurement_count integer NOT NULL CHECK (measurement_count = 3),
    accepted_photo_review_count integer NOT NULL CHECK (accepted_photo_review_count = 3),
    minimum_height_cm numeric(7,2) NOT NULL CHECK (minimum_height_cm >= 0),
    maximum_height_cm numeric(7,2) NOT NULL CHECK (maximum_height_cm >= minimum_height_cm),
    mean_height_cm numeric(9,4) NOT NULL CHECK (mean_height_cm >= minimum_height_cm),
    n1_count integer NOT NULL CHECK (n1_count >= 0),
    n2_count integer NOT NULL CHECK (n2_count >= 0),
    n3_count integer NOT NULL CHECK (n3_count >= 0),
    location_status text NOT NULL CHECK (location_status = 'simulated'),
    evidence_status text NOT NULL CHECK (evidence_status = 'prepared_reviewed_non_operational'),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    eligible_for_field_evidence boolean NOT NULL CHECK (NOT eligible_for_field_evidence),
    eligible_for_model_training boolean NOT NULL CHECK (NOT eligible_for_model_training),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    generated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (n1_count + n2_count + n3_count = measurement_count)
);

CREATE FUNCTION validate_prepared_inspection_summary()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    expected record;
BEGIN
    SELECT
        count(DISTINCT measurement.planned_point_id)::integer AS measurement_count,
        min(measurement.height_cm) AS minimum_height_cm,
        max(measurement.height_cm) AS maximum_height_cm,
        avg(measurement.height_cm)::numeric(9,4) AS mean_height_cm,
        count(*) FILTER (WHERE measurement.height_cm < policy.n1_upper_exclusive_cm)::integer AS n1_count,
        count(*) FILTER (WHERE measurement.height_cm >= policy.n1_upper_exclusive_cm
                         AND measurement.height_cm <= policy.n2_upper_inclusive_cm)::integer AS n2_count,
        count(*) FILTER (WHERE measurement.height_cm > policy.n2_upper_inclusive_cm)::integer AS n3_count
    INTO expected
    FROM prepared_inspection_summary_policy policy
    JOIN prepared_field_measurement measurement ON measurement.work_order_id = NEW.work_order_id
    WHERE policy.id = NEW.summary_policy_id
      AND policy.data_status = 'prepared'
      AND NOT policy.authorizes_field_work
    GROUP BY policy.id;

    IF expected IS NULL OR
       (expected.measurement_count, expected.minimum_height_cm,
        expected.maximum_height_cm, expected.mean_height_cm,
        expected.n1_count, expected.n2_count, expected.n3_count)
       IS DISTINCT FROM
       (NEW.measurement_count, NEW.minimum_height_cm,
        NEW.maximum_height_cm, NEW.mean_height_cm,
        NEW.n1_count, NEW.n2_count, NEW.n3_count)
    THEN
        RAISE EXCEPTION 'prepared inspection summary requires exact measurement aggregates';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM work_order order_record
        JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN app_user actor ON actor.id = NEW.generated_by_user_id
        JOIN prepared_inspection_summary_policy policy ON policy.id = NEW.summary_policy_id
        WHERE order_record.id = NEW.work_order_id
          AND order_record.status = 'prepared'
          AND order_record.data_status = 'prepared'
          AND NOT order_record.authorizes_field_work
          AND actor.status = 'active'
          AND EXISTS (
              SELECT 1 FROM road_user_role assignment
              WHERE assignment.user_id = actor.id
                AND assignment.road_id = axis.road_id
                AND assignment.role = ANY(policy.allowed_roles)
                AND assignment.data_status <> 'simulated'
          )
          AND EXISTS (
              SELECT 1 FROM prepared_work_order_demo_event finish
              WHERE finish.work_order_id = order_record.id AND finish.operation = 'finish'
          )
    ) THEN
        RAISE EXCEPTION 'prepared inspection summary requires an authorized finished demo order';
    END IF;

    IF 3 <> (
        SELECT count(DISTINCT manifest.planned_point_id)
        FROM prepared_field_photo_manifest manifest
        JOIN prepared_photo_upload_receipt receipt ON receipt.photo_id = manifest.photo_id
        JOIN prepared_photo_human_review review ON review.photo_id = receipt.photo_id
        WHERE manifest.work_order_id = NEW.work_order_id
          AND review.decision = 'accepted'
          AND review.quality_status = 'accepted'
          AND review.ruler_status = 'visible'
          AND NOT EXISTS (
              SELECT 1 FROM prepared_photo_human_review newer
              WHERE newer.supersedes_review_id = review.id
          )
    ) THEN
        RAISE EXCEPTION 'prepared inspection summary requires three effectively accepted photos';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_inspection_summary_guard
BEFORE INSERT ON prepared_inspection_summary
FOR EACH ROW EXECUTE FUNCTION validate_prepared_inspection_summary();
CREATE TRIGGER prepared_inspection_summary_immutable
BEFORE UPDATE OR DELETE ON prepared_inspection_summary
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();
CREATE TRIGGER prepared_inspection_summary_policy_immutable
BEFORE UPDATE OR DELETE ON prepared_inspection_summary_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
