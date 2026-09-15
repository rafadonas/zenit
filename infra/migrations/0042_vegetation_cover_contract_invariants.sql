BEGIN;

DO $$
DECLARE
    candidate_constraints name[];
BEGIN
    SELECT array_agg(constraint_entry.conname ORDER BY constraint_entry.conname)
    INTO candidate_constraints
    FROM pg_constraint constraint_entry
    WHERE constraint_entry.conrelid = 'vegetation_cover_observation'::regclass
      AND constraint_entry.contype = 'c'
      AND pg_get_constraintdef(constraint_entry.oid) LIKE '%cover_type%'
      AND pg_get_constraintdef(constraint_entry.oid) LIKE '%unknown_reason%';

    IF COALESCE(cardinality(candidate_constraints), 0) <> 1 THEN
        RAISE EXCEPTION
            'expected exactly one vegetation cover unknown-reason constraint, found %',
            COALESCE(cardinality(candidate_constraints), 0);
    END IF;

    EXECUTE format(
        'ALTER TABLE vegetation_cover_observation DROP CONSTRAINT %I',
        candidate_constraints[1]
    );
END;
$$;

ALTER TABLE vegetation_cover_observation
    ADD CONSTRAINT vegetation_cover_observation_unknown_reason_consistency CHECK (
        (cover_type = 'unknown' AND unknown_reason IS NOT NULL)
        OR (cover_type = 'mixed')
        OR (cover_type NOT IN ('unknown', 'mixed') AND unknown_reason IS NULL)
    ),
    ADD CONSTRAINT vegetation_cover_observation_model_version_required CHECK (
        cover_type_method <> 'model_estimated'
        OR btrim(COALESCE(model_version, '')) <> ''
    ),
    ADD CONSTRAINT vegetation_cover_observation_gps_draft_scope CHECK (
        gps_status IN ('simulated', 'unavailable')
        AND gps_accuracy_m IS NULL
    );

COMMIT;
