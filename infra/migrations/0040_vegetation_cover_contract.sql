BEGIN;

CREATE TABLE vegetation_cover_observation (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    segment_zone_id uuid NOT NULL REFERENCES segment_zone(id),
    supersedes_observation_id uuid UNIQUE REFERENCES vegetation_cover_observation(id),
    cover_type text NOT NULL CHECK (
        cover_type IN (
            'unknown', 'grass_herbaceous', 'shrub', 'tree', 'mixed', 'non_vegetation'
        )
    ),
    unknown_reason text CHECK (
        unknown_reason IN (
            'insufficient_resolution', 'shadow', 'cloud_or_haze', 'blur_or_exposure',
            'canopy_occlusion', 'vehicle_or_structure_occlusion',
            'mixed_without_dominance', 'source_conflict', 'out_of_zone',
            'privacy_redaction', 'other'
        )
    ),
    coverage_band text CHECK (
        coverage_band IN ('none', 'sparse', 'partial', 'dominant')
    ),
    visibility text CHECK (
        visibility IN ('clear', 'partially_occluded', 'mostly_occluded', 'illegible')
    ),
    dominance text CHECK (
        dominance IN ('dominant', 'co-dominant', 'not_dominant', 'not_applicable')
    ),
    spatial_relation text CHECK (
        spatial_relation IN ('inside_zone', 'overhang', 'adjacent', 'uncertain')
    ),
    cover_type_method text NOT NULL CHECK (
        cover_type_method IN ('model_estimated', 'human_reviewed')
    ),
    source_type text NOT NULL CHECK (
        source_type IN ('satellite', 'field_photo', 'manual_annotation', 'model_output', 'other')
    ),
    source_reference text NOT NULL CHECK (btrim(source_reference) <> ''),
    source_acquired_at timestamptz,
    source_checksum_sha256 char(64) CHECK (
        source_checksum_sha256 IS NULL OR source_checksum_sha256 ~ '^[0-9a-f]{64}$'
    ),
    validity_status text NOT NULL CHECK (
        validity_status IN ('valid', 'limited', 'invalid')
    ),
    confidence_band text NOT NULL CHECK (confidence_band IN ('low', 'medium', 'high')),
    quality_status text NOT NULL CHECK (quality_status IN ('accepted', 'limited', 'rejected')),
    review_state text NOT NULL DEFAULT 'pending' CHECK (
        review_state IN ('pending', 'accepted', 'corrected', 'rejected')
    ),
    taxonomy_version text NOT NULL CHECK (btrim(taxonomy_version) <> ''),
    model_version text,
    rationale text,
    gps_status text NOT NULL DEFAULT 'unavailable' CHECK (
        gps_status IN ('real', 'simulated', 'unavailable')
    ),
    gps_accuracy_m numeric(8, 2) CHECK (gps_accuracy_m >= 0),
    data_status text NOT NULL DEFAULT 'prepared' CHECK (
        data_status IN ('real', 'estimated', 'simulated', 'prepared', 'inconclusive')
    ),
    provenance jsonb NOT NULL DEFAULT '{}'::jsonb,
    eligible_for_official_reporting boolean NOT NULL DEFAULT false,
    reviewed_by_user_id uuid REFERENCES app_user(id),
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((cover_type = 'unknown') = (unknown_reason IS NOT NULL)),
    CHECK (
        cover_type NOT IN ('unknown', 'mixed')
        OR btrim(COALESCE(rationale, '')) <> ''
    ),
    CHECK (
        (review_state = 'pending' AND reviewed_by_user_id IS NULL AND reviewed_at IS NULL)
        OR (review_state <> 'pending' AND reviewed_by_user_id IS NOT NULL AND reviewed_at IS NOT NULL)
    ),
    CHECK (jsonb_typeof(provenance) = 'object'),
    CHECK (NOT eligible_for_official_reporting),
    CHECK (supersedes_observation_id IS NULL OR supersedes_observation_id <> id)
);

CREATE INDEX vegetation_cover_observation_zone_idx
    ON vegetation_cover_observation (segment_zone_id, created_at DESC);
CREATE INDEX vegetation_cover_observation_review_idx
    ON vegetation_cover_observation (review_state, created_at DESC);

CREATE FUNCTION validate_vegetation_cover_observation_chain()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    superseded_zone_id uuid;
BEGIN
    IF NEW.supersedes_observation_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT segment_zone_id
    INTO superseded_zone_id
    FROM vegetation_cover_observation
    WHERE id = NEW.supersedes_observation_id;

    IF superseded_zone_id IS DISTINCT FROM NEW.segment_zone_id THEN
        RAISE EXCEPTION 'a vegetation cover observation can only supersede an observation in the same zone';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER vegetation_cover_observation_chain_guard
BEFORE INSERT ON vegetation_cover_observation
FOR EACH ROW EXECUTE FUNCTION validate_vegetation_cover_observation_chain();

CREATE FUNCTION prevent_vegetation_cover_observation_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'vegetation cover observations are append-only; insert a superseding observation';
END;
$$;

CREATE TRIGGER vegetation_cover_observation_immutable
BEFORE UPDATE OR DELETE ON vegetation_cover_observation
FOR EACH ROW EXECUTE FUNCTION prevent_vegetation_cover_observation_mutation();

COMMIT;
