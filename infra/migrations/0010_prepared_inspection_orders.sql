BEGIN;

CREATE TABLE inspection_order_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL,
    planned_point_fractions double precision[] NOT NULL,
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    data_status text NOT NULL CHECK (data_status IN ('prepared', 'real')),
    policy_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(allowed_roles) > 0),
    CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    CHECK (cardinality(planned_point_fractions) = 3),
    CONSTRAINT inspection_order_policy_point_fraction_bounds CHECK (
        array_lower(planned_point_fractions, 1) = 1
        AND array_upper(planned_point_fractions, 1) = 3
    ),
    CHECK (
        planned_point_fractions[1] > 0
        AND planned_point_fractions[1] < planned_point_fractions[2]
        AND planned_point_fractions[2] < planned_point_fractions[3]
        AND planned_point_fractions[3] < 1
    ),
    CHECK (jsonb_typeof(policy_metadata) = 'object')
);

INSERT INTO inspection_order_policy (
    id,
    version,
    allowed_roles,
    planned_point_fractions,
    authorizes_field_work,
    data_status,
    policy_metadata
) VALUES (
    '91000000-0000-4000-8000-000000000001',
    'prepared-inspection-order-v1',
    ARRAY['manager', 'supervisor'],
    ARRAY[1.0 / 6.0, 0.5, 5.0 / 6.0]::double precision[],
    false,
    'prepared',
    '{
        "official_motiva_policy": false,
        "scope": "prepared_inspection_order_only",
        "planning_method": "segment_centerline_fraction",
        "point_locations_are_operational": false
    }'::jsonb
);

CREATE TABLE work_order (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_review_id uuid NOT NULL UNIQUE REFERENCES recommendation_review(id),
    segment_zone_id uuid NOT NULL REFERENCES segment_zone(id),
    creation_policy_id uuid NOT NULL REFERENCES inspection_order_policy(id),
    created_by_user_id uuid NOT NULL REFERENCES app_user(id),
    idempotency_key char(64) NOT NULL UNIQUE,
    order_type text NOT NULL DEFAULT 'inspection' CHECK (order_type = 'inspection'),
    status text NOT NULL DEFAULT 'prepared' CHECK (status = 'prepared'),
    version integer NOT NULL DEFAULT 1 CHECK (version = 1),
    planning_rationale text NOT NULL CHECK (btrim(planning_rationale) <> ''),
    data_status text NOT NULL DEFAULT 'prepared' CHECK (data_status = 'prepared'),
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    eligible_for_field_execution boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_field_execution),
    eligible_for_official_reporting boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_official_reporting),
    order_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    CHECK (jsonb_typeof(order_metadata) = 'object')
);

CREATE INDEX work_order_zone_idx ON work_order (segment_zone_id, created_at DESC);
CREATE INDEX work_order_creator_idx ON work_order (created_by_user_id, created_at DESC);

CREATE TABLE work_order_planned_point (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id uuid NOT NULL REFERENCES work_order(id),
    sequence integer NOT NULL CHECK (sequence BETWEEN 1 AND 3),
    position_fraction double precision NOT NULL
        CHECK (position_fraction > 0 AND position_fraction < 1),
    planned_geometry geometry(Point, 31983) NOT NULL,
    planning_method text NOT NULL CHECK (planning_method = 'segment_centerline_fraction'),
    data_status text NOT NULL
        CHECK (data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')),
    eligible_for_field_execution boolean NOT NULL DEFAULT false
        CHECK (NOT eligible_for_field_execution),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (work_order_id, sequence),
    UNIQUE (work_order_id, position_fraction),
    CHECK (ST_IsValid(planned_geometry))
);

CREATE INDEX work_order_planned_point_gix
    ON work_order_planned_point USING gist (planned_geometry);

CREATE FUNCTION validate_prepared_inspection_order()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_zone_id uuid;
    target_road_id uuid;
    effective_action text;
    source_review_policy_id uuid;
    policy_allowed_roles text[];
BEGIN
    SELECT
        analysis.segment_zone_id,
        axis.road_id,
        CASE
            WHEN review.decision = 'accepted' THEN analysis.recommendation
            WHEN review.decision = 'adjusted' THEN review.adjusted_recommendation
            ELSE NULL
        END,
        review.review_policy_id
    INTO target_zone_id, target_road_id, effective_action, source_review_policy_id
    FROM recommendation_review review
    JOIN vegetation_analysis analysis ON analysis.id = review.vegetation_analysis_id
    JOIN segment_zone zone ON zone.id = analysis.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    WHERE review.id = NEW.source_review_id;

    IF NOT FOUND OR source_review_policy_id IS NULL THEN
        RAISE EXCEPTION 'a prepared inspection order requires a versioned source review';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM recommendation_review correction
        WHERE correction.supersedes_review_id = NEW.source_review_id
    ) THEN
        RAISE EXCEPTION 'a prepared inspection order requires the effective review';
    END IF;

    IF effective_action IS DISTINCT FROM 'inspect' THEN
        RAISE EXCEPTION 'only an effective inspection decision can create an inspection order';
    END IF;

    IF NEW.segment_zone_id <> target_zone_id THEN
        RAISE EXCEPTION 'inspection order zone must match its source review';
    END IF;

    SELECT allowed_roles
    INTO policy_allowed_roles
    FROM inspection_order_policy
    WHERE id = NEW.creation_policy_id
      AND NOT authorizes_field_work
      AND data_status = 'prepared';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared inspection-order policy is unavailable';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM app_user reviewer
        JOIN road_user_role assignment ON assignment.user_id = reviewer.id
        WHERE reviewer.id = NEW.created_by_user_id
          AND reviewer.status = 'active'
          AND assignment.road_id = target_road_id
          AND assignment.role = ANY(policy_allowed_roles)
          AND assignment.data_status <> 'simulated'
    ) THEN
        RAISE EXCEPTION 'inspection-order creator lacks an eligible road role';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_inspection_order_guard
BEFORE INSERT ON work_order
FOR EACH ROW EXECUTE FUNCTION validate_prepared_inspection_order();

CREATE FUNCTION validate_work_order_planned_point()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    source_line geometry(LineString, 31983);
    source_data_status text;
    expected_fraction double precision;
BEGIN
    SELECT
        segment.metric_geometry,
        segment.data_status,
        policy.planned_point_fractions[NEW.sequence]
    INTO source_line, source_data_status, expected_fraction
    FROM work_order order_record
    JOIN inspection_order_policy policy ON policy.id = order_record.creation_policy_id
    JOIN segment_zone zone ON zone.id = order_record.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    WHERE order_record.id = NEW.work_order_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'planned point requires an inspection order';
    END IF;

    IF abs(NEW.position_fraction - expected_fraction) > 0.000000001 THEN
        RAISE EXCEPTION 'planned point fraction must match the versioned policy';
    END IF;

    IF NEW.data_status <> source_data_status THEN
        RAISE EXCEPTION 'planned point must preserve the source segment data status';
    END IF;

    IF ST_Distance(
        NEW.planned_geometry,
        ST_LineInterpolatePoint(source_line, NEW.position_fraction)
    ) > 0.001 THEN
        RAISE EXCEPTION 'planned point must use the declared centerline-fraction method';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER work_order_planned_point_guard
BEFORE INSERT ON work_order_planned_point
FOR EACH ROW EXECUTE FUNCTION validate_work_order_planned_point();

CREATE FUNCTION validate_work_order_point_count()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    expected_count integer;
    actual_count integer;
    target_work_order_id uuid;
BEGIN
    target_work_order_id := NEW.id;

    SELECT cardinality(policy.planned_point_fractions)
    INTO expected_count
    FROM work_order order_record
    JOIN inspection_order_policy policy ON policy.id = order_record.creation_policy_id
    WHERE order_record.id = target_work_order_id;

    SELECT count(*)
    INTO actual_count
    FROM work_order_planned_point point
    WHERE point.work_order_id = target_work_order_id;

    IF expected_count IS NULL OR actual_count <> expected_count THEN
        RAISE EXCEPTION 'prepared inspection order requires exactly three planned points';
    END IF;

    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER work_order_point_count_guard
AFTER INSERT ON work_order
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_work_order_point_count();

CREATE FUNCTION prevent_prepared_inspection_order_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'prepared inspection orders are immutable; create a versioned event';
END;
$$;

CREATE TRIGGER inspection_order_policy_immutable
BEFORE UPDATE OR DELETE ON inspection_order_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_inspection_order_mutation();

CREATE TRIGGER work_order_immutable
BEFORE UPDATE OR DELETE ON work_order
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_inspection_order_mutation();

CREATE TRIGGER work_order_planned_point_immutable
BEFORE UPDATE OR DELETE ON work_order_planned_point
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_inspection_order_mutation();

COMMIT;
