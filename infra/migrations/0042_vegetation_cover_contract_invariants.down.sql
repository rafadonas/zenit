BEGIN;

ALTER TABLE vegetation_cover_observation
    DROP CONSTRAINT IF EXISTS vegetation_cover_observation_gps_draft_scope,
    DROP CONSTRAINT IF EXISTS vegetation_cover_observation_model_version_required,
    DROP CONSTRAINT IF EXISTS vegetation_cover_observation_unknown_reason_consistency,
    ADD CONSTRAINT vegetation_cover_observation_unknown_reason_original CHECK (
        (cover_type = 'unknown') = (unknown_reason IS NOT NULL)
    );

COMMIT;
