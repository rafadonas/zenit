BEGIN;

CREATE TABLE app_user (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL CHECK (btrim(email) = email AND position('@' IN email) > 1),
    password_hash text NOT NULL CHECK (btrim(password_hash) <> ''),
    display_name text NOT NULL CHECK (btrim(display_name) <> ''),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
    identity_source text NOT NULL DEFAULT 'local_mvp'
        CHECK (identity_source IN ('local_mvp', 'corporate_future')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX app_user_email_lower_idx ON app_user (lower(email));

CREATE TABLE road_user_role (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES app_user(id),
    road_id uuid NOT NULL REFERENCES road(id),
    role text NOT NULL CHECK (role IN ('manager', 'supervisor')),
    data_status text NOT NULL DEFAULT 'prepared'
        CHECK (data_status IN ('real', 'prepared', 'simulated')),
    granted_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, road_id, role)
);

CREATE INDEX road_user_role_scope_idx ON road_user_role (road_id, role, user_id);

CREATE TABLE recommendation_review_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL,
    requires_authenticated_identity boolean NOT NULL,
    dual_approval_required boolean NOT NULL DEFAULT false,
    authorizes_field_work boolean NOT NULL DEFAULT false CHECK (NOT authorizes_field_work),
    data_status text NOT NULL CHECK (data_status IN ('prepared', 'real')),
    policy_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(allowed_roles) > 0),
    CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    CHECK (jsonb_typeof(policy_metadata) = 'object')
);

INSERT INTO recommendation_review_policy (
    id,
    version,
    allowed_roles,
    requires_authenticated_identity,
    dual_approval_required,
    authorizes_field_work,
    data_status,
    policy_metadata
) VALUES (
    '90000000-0000-4000-8000-000000000001',
    'recommendation-review-mvp-v1',
    ARRAY['manager', 'supervisor'],
    true,
    false,
    false,
    'prepared',
    '{"official_motiva_policy": false, "scope": "recommendation_review_only"}'::jsonb
);

ALTER TABLE recommendation_review
    ADD COLUMN reviewer_user_id uuid REFERENCES app_user(id),
    ADD COLUMN review_policy_id uuid REFERENCES recommendation_review_policy(id),
    ADD CONSTRAINT recommendation_review_identity_consistency CHECK (
        reviewer_user_id IS NULL OR reviewer_subject = reviewer_user_id::text
    );

CREATE FUNCTION validate_recommendation_review_identity_and_policy()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    policy_requires_identity boolean;
    policy_allowed_roles text[];
    target_road_id uuid;
BEGIN
    IF NEW.review_policy_id IS NULL THEN
        RAISE EXCEPTION 'new recommendation reviews require a versioned review policy';
    END IF;

    SELECT requires_authenticated_identity, allowed_roles
    INTO policy_requires_identity, policy_allowed_roles
    FROM recommendation_review_policy
    WHERE id = NEW.review_policy_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'recommendation review policy does not exist';
    END IF;

    IF NOT policy_requires_identity THEN
        RETURN NEW;
    END IF;

    IF NEW.reviewer_user_id IS NULL OR NEW.reviewer_subject <> NEW.reviewer_user_id::text THEN
        RAISE EXCEPTION 'authenticated recommendation reviews require a consistent user identity';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM app_user
        WHERE id = NEW.reviewer_user_id
          AND status = 'active'
    ) THEN
        RAISE EXCEPTION 'recommendation reviewer is not an active user';
    END IF;

    SELECT axis.road_id
    INTO target_road_id
    FROM vegetation_analysis analysis
    JOIN segment_zone zone ON zone.id = analysis.segment_zone_id
    JOIN road_segment segment ON segment.id = zone.road_segment_id
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    WHERE analysis.id = NEW.vegetation_analysis_id;

    IF NOT EXISTS (
        SELECT 1
        FROM road_user_role assignment
        WHERE assignment.user_id = NEW.reviewer_user_id
          AND assignment.road_id = target_road_id
          AND assignment.role = ANY(policy_allowed_roles)
    ) THEN
        RAISE EXCEPTION 'recommendation reviewer lacks the required road role';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER recommendation_review_identity_policy_guard
BEFORE INSERT ON recommendation_review
FOR EACH ROW EXECUTE FUNCTION validate_recommendation_review_identity_and_policy();

CREATE FUNCTION prevent_recommendation_review_policy_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'recommendation review policies are immutable; insert a new version';
END;
$$;

CREATE TRIGGER recommendation_review_policy_immutable
BEFORE UPDATE OR DELETE ON recommendation_review_policy
FOR EACH ROW EXECUTE FUNCTION prevent_recommendation_review_policy_mutation();

COMMIT;
