BEGIN;

CREATE TABLE prepared_mowing_post_service_summary_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL,
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    policy_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    CHECK (cardinality(allowed_roles) > 0),
    CHECK (jsonb_typeof(policy_metadata) = 'object')
);

INSERT INTO prepared_mowing_post_service_summary_policy
    (id, version, allowed_roles, data_status, authorizes_field_work, policy_metadata)
VALUES
    ('90000000-0000-4000-8000-000000000008',
     'prepared-mowing-post-service-summary-v1',
     ARRAY['manager', 'supervisor'], 'prepared', false,
     '{"official_motiva_policy":false,"scope":"simulated_mowing_post_service_summary_only"}'::jsonb);

CREATE TABLE prepared_mowing_post_service_summary (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mowing_order_id uuid NOT NULL UNIQUE REFERENCES prepared_mowing_order(id),
    generated_by_user_id uuid NOT NULL REFERENCES app_user(id),
    summary_policy_id uuid NOT NULL REFERENCES prepared_mowing_post_service_summary_policy(id),
    idempotency_key char(64) NOT NULL UNIQUE CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    generation_rationale text NOT NULL CHECK (btrim(generation_rationale) <> ''),
    measurement_count integer NOT NULL CHECK (measurement_count = 3),
    accepted_photo_review_count integer NOT NULL CHECK (accepted_photo_review_count = 3),
    minimum_height_cm numeric(7,2) NOT NULL CHECK (minimum_height_cm >= 0),
    maximum_height_cm numeric(7,2) NOT NULL CHECK (maximum_height_cm >= minimum_height_cm),
    mean_height_cm numeric(9,4) NOT NULL CHECK (mean_height_cm >= minimum_height_cm AND mean_height_cm <= maximum_height_cm),
    n1_count integer NOT NULL CHECK (n1_count >= 0),
    n2_count integer NOT NULL CHECK (n2_count >= 0),
    n3_count integer NOT NULL CHECK (n3_count >= 0),
    phase text NOT NULL CHECK (phase = 'post_service'),
    summary_scope text NOT NULL CHECK (summary_scope = 'mowing_demo_post_service_only'),
    location_status text NOT NULL CHECK (location_status = 'not_collected'),
    data_status text NOT NULL CHECK (data_status = 'simulated'),
    evidence_status text NOT NULL CHECK (evidence_status = 'simulated_reviewed_non_operational'),
    eligible_for_field_evidence boolean NOT NULL CHECK (NOT eligible_for_field_evidence),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    eligible_for_model_training boolean NOT NULL CHECK (NOT eligible_for_model_training),
    eligible_for_official_reporting boolean NOT NULL CHECK (NOT eligible_for_official_reporting),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    generated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (n1_count + n2_count + n3_count = measurement_count)
);

CREATE FUNCTION validate_prepared_mowing_post_service_summary()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected record; accepted_count integer; road_id uuid; roles text[];
BEGIN
    SELECT policy.allowed_roles INTO roles
    FROM prepared_mowing_post_service_summary_policy policy
    WHERE policy.id = NEW.summary_policy_id AND policy.data_status = 'prepared'
      AND NOT policy.authorizes_field_work;
    IF NOT FOUND THEN RAISE EXCEPTION 'post-service summary requires active prepared policy'; END IF;

    SELECT axis.road_id INTO road_id
    FROM prepared_mowing_order mowing
    JOIN work_order inspection ON inspection.id = mowing.source_inspection_work_order_id
    JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    WHERE mowing.id = NEW.mowing_order_id AND mowing.status = 'prepared'
      AND mowing.data_status = 'prepared' AND mowing.location_status = 'simulated'
      AND mowing.requires_operational_approval AND NOT mowing.authorizes_field_work
      AND NOT mowing.eligible_for_field_execution AND NOT mowing.eligible_for_official_reporting;
    IF road_id IS NULL THEN RAISE EXCEPTION 'post-service summary target is not prepared'; END IF;
    IF NOT EXISTS (SELECT 1 FROM road_user_role assignment WHERE assignment.user_id = NEW.generated_by_user_id AND assignment.road_id = road_id AND assignment.role = ANY(roles) AND assignment.data_status <> 'simulated') THEN
        RAISE EXCEPTION 'post-service summary actor lacks road role';
    END IF;

    SELECT count(*)::integer AS count, min(height_cm), max(height_cm), avg(height_cm)::numeric(9,4) AS mean,
           count(*) FILTER (WHERE height_cm < 10)::integer AS n1,
           count(*) FILTER (WHERE height_cm >= 10 AND height_cm <= 30)::integer AS n2,
           count(*) FILTER (WHERE height_cm > 30)::integer AS n3
    INTO expected FROM prepared_mowing_post_service_measurement measurement
    WHERE measurement.mowing_order_id = NEW.mowing_order_id;
    SELECT count(*)::integer INTO accepted_count
    FROM prepared_mowing_post_service_photo_manifest manifest
    JOIN prepared_mowing_post_service_photo_upload_receipt receipt ON receipt.photo_id = manifest.photo_id
    JOIN prepared_mowing_post_service_photo_human_review review ON review.photo_id = manifest.photo_id
    WHERE manifest.mowing_order_id = NEW.mowing_order_id AND receipt.content_status = 'uploaded_unverified'
      AND review.decision = 'accepted' AND review.quality_status = 'accepted' AND review.ruler_status = 'visible'
      AND NOT EXISTS (SELECT 1 FROM prepared_mowing_post_service_photo_human_review newer WHERE newer.supersedes_review_id = review.id);
    IF expected.count <> 3 OR accepted_count <> 3 THEN RAISE EXCEPTION 'post-service summary requires three measurements and accepted photo reviews'; END IF;
    IF (NEW.minimum_height_cm, NEW.maximum_height_cm, NEW.mean_height_cm, NEW.n1_count, NEW.n2_count, NEW.n3_count) <> (expected.min, expected.max, expected.mean, expected.n1, expected.n2, expected.n3) THEN
        RAISE EXCEPTION 'post-service summary requires exact measurement aggregates';
    END IF;
    RETURN NEW;
END; $$;

CREATE TRIGGER prepared_mowing_post_service_summary_guard BEFORE INSERT ON prepared_mowing_post_service_summary
FOR EACH ROW EXECUTE FUNCTION validate_prepared_mowing_post_service_summary();
CREATE TRIGGER prepared_mowing_post_service_summary_immutable BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_summary
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();
CREATE TRIGGER prepared_mowing_post_service_summary_policy_immutable BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_summary_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
