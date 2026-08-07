BEGIN;

INSERT INTO road (code, name)
VALUES ('SP021', 'Rodoanel Oeste')
ON CONFLICT (code) DO NOTHING;

WITH successful_marker_run AS (
    SELECT r.id
    FROM import_run r
    JOIN import_job j ON j.id = r.import_job_id
    WHERE j.parser_name = 'km-markers' AND r.status = 'succeeded'
    ORDER BY r.finished_at DESC NULLS LAST
    LIMIT 1
),
marker_stats AS (
    SELECT
        r.id AS road_id,
        smr.import_run_id,
        ST_MakeLine(smr.original_geometry ORDER BY smr.kilometer) AS source_geometry,
        count(*) AS marker_count
    FROM staging_km_marker smr
    JOIN successful_marker_run success ON success.id = smr.import_run_id
    CROSS JOIN road r
    WHERE r.code = 'SP021'
    GROUP BY r.id, smr.import_run_id
),
gap_stats AS (
    SELECT
        import_run_id,
        max(gap_m) AS max_marker_gap_m,
        avg(gap_m) AS average_marker_gap_m
    FROM (
        SELECT
            import_run_id,
            ST_Distance(
                ST_Transform(
                    lag(original_geometry) OVER (
                        PARTITION BY import_run_id ORDER BY kilometer
                    ),
                    31983
                ),
                ST_Transform(original_geometry, 31983)
            ) AS gap_m
        FROM staging_km_marker
    ) gaps
    WHERE gap_m IS NOT NULL
    GROUP BY import_run_id
),
candidate AS (
    INSERT INTO road_axis_candidate (
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
    )
    SELECT
        markers.road_id,
        markers.import_run_id,
        1,
        'ordered_km_marker_straight_line',
        'needs_validation',
        'estimated',
        false,
        markers.source_geometry,
        ST_Transform(markers.source_geometry, 31983),
        ST_Length(ST_Transform(markers.source_geometry, 31983)),
        jsonb_build_object(
            'marker_count', markers.marker_count,
            'expected_marker_interval_m', 1000,
            'max_marker_gap_m', gaps.max_marker_gap_m,
            'average_marker_gap_m', gaps.average_marker_gap_m,
            'known_label_issue', 'km 2 and km 3 are spatially reversed',
            'operational_blocker', true
        )
    FROM marker_stats markers
    JOIN gap_stats gaps ON gaps.import_run_id = markers.import_run_id
    ON CONFLICT (road_id, source_import_run_id, version) DO UPDATE
    SET quality_metrics = EXCLUDED.quality_metrics
    RETURNING id, metric_geometry, length_m
),
selected_candidate AS (
    SELECT id, metric_geometry, length_m FROM candidate
    UNION ALL
    SELECT axis.id, axis.metric_geometry, axis.length_m
    FROM road_axis_candidate axis
    JOIN marker_stats markers
      ON markers.road_id = axis.road_id
     AND markers.import_run_id = axis.source_import_run_id
    WHERE axis.version = 1
      AND NOT EXISTS (SELECT 1 FROM candidate)
),
segment_starts AS (
    SELECT
        axis.id,
        axis.metric_geometry,
        axis.length_m,
        generate_series(0, ceil(axis.length_m / 100.0)::integer - 1) AS segment_index
    FROM selected_candidate axis
)
INSERT INTO road_segment (
    road_axis_candidate_id,
    segment_index,
    start_distance_m,
    end_distance_m,
    metric_geometry,
    data_status,
    eligible_for_operations
)
SELECT
    id,
    segment_index,
    segment_index * 100.0,
    least((segment_index + 1) * 100.0, length_m),
    ST_LineSubstring(
        metric_geometry,
        (segment_index * 100.0) / length_m,
        least(((segment_index + 1) * 100.0) / length_m, 1.0)
    ),
    'estimated',
    false
FROM segment_starts
ON CONFLICT (road_axis_candidate_id, segment_index) DO NOTHING;

COMMIT;
