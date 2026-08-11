BEGIN;

CREATE TABLE prepared_photo_review_policy (
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

INSERT INTO prepared_photo_review_policy (
    id, version, allowed_roles, requires_authenticated_identity,
    authorizes_field_work, data_status, policy_metadata
) VALUES (
    '90000000-0000-4000-8000-000000000004',
    'prepared-photo-review-v1',
    ARRAY['manager', 'supervisor'],
    true,
    false,
    'prepared',
    '{"official_motiva_policy":false,"scope":"prepared_human_photo_review_only"}'::jsonb
);

CREATE TABLE prepared_photo_human_review (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_id uuid NOT NULL REFERENCES prepared_photo_upload_receipt(photo_id),
    supersedes_review_id uuid UNIQUE REFERENCES prepared_photo_human_review(id),
    reviewer_user_id uuid NOT NULL REFERENCES app_user(id),
    review_policy_id uuid NOT NULL REFERENCES prepared_photo_review_policy(id),
    idempotency_key char(64) NOT NULL UNIQUE
        CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    decision text NOT NULL CHECK (decision IN ('accepted', 'rejected', 'inconclusive')),
    quality_status text NOT NULL
        CHECK (quality_status IN ('accepted', 'rejected', 'inconclusive')),
    ruler_status text NOT NULL
        CHECK (ruler_status IN ('visible', 'not_visible', 'inconclusive')),
    rationale text,
    source_channel text NOT NULL CHECK (source_channel = 'api'),
    data_status text NOT NULL CHECK (data_status = 'prepared'),
    eligible_for_field_evidence boolean NOT NULL CHECK (NOT eligible_for_field_evidence),
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

CREATE INDEX prepared_photo_human_review_photo_idx
    ON prepared_photo_human_review (photo_id, reviewed_at DESC);
CREATE INDEX prepared_photo_human_review_reviewer_idx
    ON prepared_photo_human_review (reviewer_user_id, reviewed_at DESC);

CREATE FUNCTION validate_prepared_photo_human_review()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    policy_roles text[];
BEGIN
    SELECT allowed_roles INTO policy_roles
    FROM prepared_photo_review_policy
    WHERE id = NEW.review_policy_id
      AND requires_authenticated_identity
      AND NOT authorizes_field_work
      AND data_status = 'prepared';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'prepared photo review requires an active prepared policy';
    END IF;

    IF NEW.supersedes_review_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM prepared_photo_human_review prior
        WHERE prior.id = NEW.supersedes_review_id
          AND prior.photo_id = NEW.photo_id
    ) THEN
        RAISE EXCEPTION 'prepared photo review can only supersede the same photo';
    END IF;

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
        JOIN app_user actor ON actor.id = NEW.reviewer_user_id
        WHERE receipt.photo_id = NEW.photo_id
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
                AND assignment.role = ANY(policy_roles)
                AND assignment.data_status <> 'simulated'
          )
    ) THEN
        RAISE EXCEPTION 'prepared photo review requires an authorized uploaded receipt';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_photo_human_review_guard
BEFORE INSERT ON prepared_photo_human_review
FOR EACH ROW EXECUTE FUNCTION validate_prepared_photo_human_review();

CREATE TRIGGER prepared_photo_human_review_immutable
BEFORE UPDATE OR DELETE ON prepared_photo_human_review
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

CREATE TRIGGER prepared_photo_review_policy_immutable
BEFORE UPDATE OR DELETE ON prepared_photo_review_policy
FOR EACH ROW EXECUTE FUNCTION prevent_prepared_mobile_sync_mutation();

COMMIT;
