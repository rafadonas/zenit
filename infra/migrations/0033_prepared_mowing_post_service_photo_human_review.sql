BEGIN;

CREATE TABLE prepared_mowing_post_service_photo_review_policy (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version text NOT NULL UNIQUE CHECK (btrim(version) <> ''),
    allowed_roles text[] NOT NULL,
    requires_authenticated_identity boolean NOT NULL CHECK (requires_authenticated_identity),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    policy_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(allowed_roles) > 0),
    CHECK (allowed_roles <@ ARRAY['manager', 'supervisor']::text[]),
    CHECK (jsonb_typeof(policy_metadata) = 'object')
);

INSERT INTO prepared_mowing_post_service_photo_review_policy (
    id, version, allowed_roles, requires_authenticated_identity,
    authorizes_field_work, data_status, policy_metadata
) VALUES (
    '90000000-0000-4000-8000-000000000007',
    'prepared-mowing-post-service-photo-review-v1',
    ARRAY['manager', 'supervisor'],
    true,
    false,
    'prepared',
    '{"official_motiva_policy":false,"scope":"simulated_mowing_post_service_photo_review_only"}'::jsonb
);

CREATE TABLE prepared_mowing_post_service_photo_human_review (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id uuid NOT NULL
        REFERENCES prepared_mowing_post_service_photo_upload_receipt(photo_id),
    supersedes_review_id uuid UNIQUE
        REFERENCES prepared_mowing_post_service_photo_human_review(id),
    reviewer_user_id uuid NOT NULL REFERENCES app_user(id),
    review_policy_id uuid NOT NULL
        REFERENCES prepared_mowing_post_service_photo_review_policy(id),
    idempotency_key char(64) NOT NULL UNIQUE
        CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    decision text NOT NULL CHECK (decision IN ('accepted', 'rejected', 'inconclusive')),
    quality_status text NOT NULL
        CHECK (quality_status IN ('accepted', 'rejected', 'inconclusive')),
    ruler_status text NOT NULL
        CHECK (ruler_status IN ('visible', 'not_visible', 'inconclusive')),
    rationale text,
    source_channel text NOT NULL CHECK (source_channel = 'api'),
    phase text NOT NULL CHECK (phase = 'post_service'),
    photo_scope text NOT NULL CHECK (photo_scope = 'mowing_demo_post_service_only'),
    location_status text NOT NULL CHECK (location_status = 'not_collected'),
    data_status text NOT NULL CHECK (data_status = 'simulated'),
    operational_approval_satisfied boolean NOT NULL
        CHECK (NOT operational_approval_satisfied),
    eligible_for_field_evidence boolean NOT NULL CHECK (NOT eligible_for_field_evidence),
    eligible_for_field_execution boolean NOT NULL CHECK (NOT eligible_for_field_execution),
    eligible_for_model_training boolean NOT NULL CHECK (NOT eligible_for_model_training),
    eligible_for_official_reporting boolean NOT NULL
        CHECK (NOT eligible_for_official_reporting),
    authorizes_field_work boolean NOT NULL CHECK (NOT authorizes_field_work),
    reviewed_at timestamptz NOT NULL DEFAULT now(),
    CHECK (supersedes_review_id IS NULL OR supersedes_review_id <> id),
    CHECK ((decision = 'accepted') =
        (quality_status = 'accepted' AND ruler_status = 'visible')),
    CHECK (decision = 'accepted' OR btrim(COALESCE(rationale, '')) <> '')
);

CREATE INDEX prepared_mowing_post_service_photo_review_photo_idx
    ON prepared_mowing_post_service_photo_human_review (photo_id, reviewed_at DESC);
CREATE INDEX prepared_mowing_post_service_photo_review_reviewer_idx
    ON prepared_mowing_post_service_photo_human_review (reviewer_user_id, reviewed_at DESC);

CREATE FUNCTION validate_prepared_mowing_post_service_photo_human_review()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    policy_roles text[];
    prior_count integer;
BEGIN
    PERFORM pg_advisory_xact_lock(
        hashtextextended('prepared-mowing-photo-review:' || NEW.photo_id, 0)
    );

    SELECT allowed_roles INTO policy_roles
    FROM prepared_mowing_post_service_photo_review_policy
    WHERE id = NEW.review_policy_id
      AND requires_authenticated_identity
      AND NOT authorizes_field_work
      AND data_status = 'prepared';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'simulated mowing photo review requires an active prepared policy';
    END IF;

    IF NEW.supersedes_review_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM prepared_mowing_post_service_photo_human_review prior
        WHERE prior.id = NEW.supersedes_review_id
          AND prior.photo_id = NEW.photo_id
    ) THEN
        RAISE EXCEPTION 'simulated mowing photo review can only supersede the same photo';
    END IF;

    SELECT count(*) INTO prior_count
    FROM prepared_mowing_post_service_photo_human_review
    WHERE photo_id = NEW.photo_id;

    IF prior_count = 0 AND NEW.supersedes_review_id IS NOT NULL THEN
        RAISE EXCEPTION 'first simulated mowing photo review cannot supersede another review';
    ELSIF prior_count > 0 AND NEW.supersedes_review_id IS NULL THEN
        RAISE EXCEPTION 'subsequent simulated mowing photo review must supersede the effective review';
    ELSIF prior_count > 0 AND EXISTS (
        SELECT 1 FROM prepared_mowing_post_service_photo_human_review newer
        WHERE newer.supersedes_review_id = NEW.supersedes_review_id
    ) THEN
        RAISE EXCEPTION 'simulated mowing photo review can only supersede the effective leaf';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM prepared_mowing_post_service_photo_upload_receipt receipt
        JOIN prepared_mowing_post_service_photo_manifest manifest
          ON manifest.photo_id = receipt.photo_id
        JOIN prepared_mowing_order mowing ON mowing.id = manifest.mowing_order_id
        JOIN work_order inspection
          ON inspection.id = mowing.source_inspection_work_order_id
        JOIN segment_zone zone ON zone.id = inspection.segment_zone_id
        JOIN road_segment segment ON segment.id = zone.road_segment_id
        JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
        JOIN app_user actor ON actor.id = NEW.reviewer_user_id
        WHERE receipt.photo_id = NEW.photo_id
          AND receipt.phase = NEW.phase
          AND receipt.photo_scope = NEW.photo_scope
          AND receipt.content_status = 'uploaded_unverified'
          AND receipt.ruler_status = 'not_validated'
          AND receipt.location_status = NEW.location_status
          AND receipt.quality_status = 'simulated_unverified'
          AND receipt.data_status = NEW.data_status
          AND receipt.operational_approval_satisfied
              = NEW.operational_approval_satisfied
          AND receipt.authorizes_field_work = NEW.authorizes_field_work
          AND receipt.eligible_for_field_execution
              = NEW.eligible_for_field_execution
          AND receipt.eligible_for_model_training
              = NEW.eligible_for_model_training
          AND receipt.eligible_for_official_reporting
              = NEW.eligible_for_official_reporting
          AND actor.status = 'active'
          AND EXISTS (
              SELECT 1 FROM road_user_role assignment
              WHERE assignment.user_id = actor.id
                AND assignment.road_id = axis.road_id
                AND assignment.role = ANY(policy_roles)
                AND assignment.data_status <> 'simulated'
          )
    ) THEN
        RAISE EXCEPTION
            'simulated mowing photo review requires an authorized uploaded receipt';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_mowing_post_service_photo_human_review_guard
BEFORE INSERT ON prepared_mowing_post_service_photo_human_review
FOR EACH ROW
EXECUTE FUNCTION validate_prepared_mowing_post_service_photo_human_review();

CREATE TRIGGER prepared_mowing_post_service_photo_human_review_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_photo_human_review
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

CREATE TRIGGER prepared_mowing_post_service_photo_review_policy_immutable
BEFORE UPDATE OR DELETE ON prepared_mowing_post_service_photo_review_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
