BEGIN;

INSERT INTO source_file (
    id,
    sha256,
    original_path,
    original_name,
    size_bytes,
    detected_format,
    storage_uri,
    data_status
) VALUES (
    '41000000-0000-4000-8000-000000000001',
    repeat('a', 64),
    'contract-test/source.json',
    'source.json',
    0,
    'json',
    'test://vegetation-cover-contract',
    'prepared'
);

INSERT INTO import_job (
    id,
    source_file_id,
    parser_name,
    parser_version,
    parameters,
    idempotency_key
) VALUES (
    '41000000-0000-4000-8000-000000000002',
    '41000000-0000-4000-8000-000000000001',
    'vegetation-cover-contract-test',
    '1',
    '{}'::jsonb,
    repeat('b', 64)
);

INSERT INTO import_run (
    id,
    import_job_id,
    attempt_number,
    status
) VALUES (
    '41000000-0000-4000-8000-000000000003',
    '41000000-0000-4000-8000-000000000002',
    1,
    'pending'
);

INSERT INTO road (id, code, name) VALUES (
    '41000000-0000-4000-8000-000000000004',
    'GEO003-TEST',
    'Vegetation cover contract test road'
);

INSERT INTO road_axis_candidate (
    id,
    road_id,
    source_import_run_id,
    version,
    derivation_method,
    validation_status,
    data_status,
    eligible_for_operations,
    source_geometry,
    metric_geometry,
    length_m,
    quality_metrics
) VALUES (
    '41000000-0000-4000-8000-000000000005',
    '41000000-0000-4000-8000-000000000004',
    '41000000-0000-4000-8000-000000000003',
    1,
    'contract_test',
    'needs_validation',
    'prepared',
    false,
    ST_GeomFromText('LINESTRING(-46 -23, -45.999 -23)', 4326),
    ST_GeomFromText('LINESTRING(0 0, 100 0)', 31983),
    100,
    '{"scope":"contract_test"}'::jsonb
);

INSERT INTO road_segment (
    id,
    road_axis_candidate_id,
    segment_index,
    start_distance_m,
    end_distance_m,
    metric_geometry,
    data_status,
    eligible_for_operations
) VALUES (
    '41000000-0000-4000-8000-000000000006',
    '41000000-0000-4000-8000-000000000005',
    0,
    0,
    100,
    ST_GeomFromText('LINESTRING(0 0, 100 0)', 31983),
    'prepared',
    false
);

INSERT INTO segment_zone (
    id,
    road_segment_id,
    zone_type,
    threshold_cm,
    data_status,
    eligible_for_operations,
    provenance
) VALUES (
    '41000000-0000-4000-8000-000000000007',
    '41000000-0000-4000-8000-000000000006',
    'left',
    30,
    'prepared',
    false,
    '{"scope":"contract_test"}'::jsonb
);

INSERT INTO vegetation_cover_observation (
    id,
    segment_zone_id,
    cover_type,
    unknown_reason,
    cover_type_method,
    source_type,
    source_reference,
    validity_status,
    confidence_band,
    quality_status,
    taxonomy_version,
    rationale,
    gps_status,
    data_status,
    provenance
) VALUES (
    '41000000-0000-4000-8000-000000000008',
    '41000000-0000-4000-8000-000000000007',
    'mixed',
    'mixed_without_dominance',
    'human_reviewed',
    'manual_annotation',
    'contract-test:mixed',
    'limited',
    'medium',
    'limited',
    'zenit-cover-taxonomy-v0.1-draft',
    'No defensible dominant cover type.',
    'unavailable',
    'prepared',
    '{"scope":"contract_test"}'::jsonb
);

INSERT INTO vegetation_cover_observation (
    id,
    segment_zone_id,
    cover_type,
    cover_type_method,
    source_type,
    source_reference,
    validity_status,
    confidence_band,
    quality_status,
    taxonomy_version,
    model_version,
    gps_status,
    data_status,
    provenance
) VALUES (
    '41000000-0000-4000-8000-000000000009',
    '41000000-0000-4000-8000-000000000007',
    'tree',
    'model_estimated',
    'model_output',
    'contract-test:model-output',
    'limited',
    'low',
    'limited',
    'zenit-cover-taxonomy-v0.1-draft',
    'contract-test-model-v1',
    'simulated',
    'prepared',
    '{"scope":"contract_test"}'::jsonb
);

DO $$
BEGIN
    BEGIN
        INSERT INTO vegetation_cover_observation (
            segment_zone_id,
            cover_type,
            cover_type_method,
            source_type,
            source_reference,
            validity_status,
            confidence_band,
            quality_status,
            taxonomy_version,
            gps_status,
            data_status,
            provenance
        ) VALUES (
            '41000000-0000-4000-8000-000000000007',
            'tree',
            'model_estimated',
            'model_output',
            'contract-test:unversioned-model',
            'limited',
            'low',
            'limited',
            'zenit-cover-taxonomy-v0.1-draft',
            'simulated',
            'prepared',
            '{"scope":"contract_test"}'::jsonb
        );
        RAISE EXCEPTION 'unversioned model estimate was accepted';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO vegetation_cover_observation (
            segment_zone_id,
            cover_type,
            cover_type_method,
            source_type,
            source_reference,
            validity_status,
            confidence_band,
            quality_status,
            taxonomy_version,
            gps_status,
            gps_accuracy_m,
            data_status,
            provenance
        ) VALUES (
            '41000000-0000-4000-8000-000000000007',
            'tree',
            'human_reviewed',
            'manual_annotation',
            'contract-test:real-gps-without-policy',
            'limited',
            'medium',
            'limited',
            'zenit-cover-taxonomy-v0.1-draft',
            'real',
            5,
            'prepared',
            '{"scope":"contract_test"}'::jsonb
        );
        RAISE EXCEPTION 'real GPS without the approved metadata contract was accepted';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;
END;
$$;

ROLLBACK;
