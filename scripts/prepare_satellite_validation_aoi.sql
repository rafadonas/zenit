BEGIN;

WITH target_segment AS (
    SELECT segment.id, segment.metric_geometry
    FROM road_segment segment
    JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
    JOIN road ON road.id = axis.road_id
    WHERE road.code = 'SP021'
      AND segment.segment_index = 195
      AND segment.data_status = 'estimated'
      AND NOT segment.eligible_for_operations
), prepared_zones(zone_type, threshold_cm, buffer_side) AS (
    VALUES
        ('left', 30.00::numeric, 'left'),
        ('right', 30.00::numeric, 'right'),
        ('median', 30.00::numeric, NULL),
        ('special', 10.00::numeric, NULL)
)
INSERT INTO segment_zone (
    road_segment_id,
    zone_type,
    metric_geometry,
    threshold_cm,
    data_status,
    eligible_for_operations,
    provenance
)
SELECT
    target.id,
    zone.zone_type,
    CASE
        WHEN zone.buffer_side IS NULL THEN NULL
        ELSE ST_Buffer(
            target.metric_geometry,
            20.0,
            format('side=%s endcap=flat join=mitre', zone.buffer_side)
        )
    END,
    zone.threshold_cm,
    'prepared',
    false,
    jsonb_build_object(
        'purpose', 'satellite_api_technical_validation',
        'derivation_method', 'single_sided_buffer_from_estimated_axis',
        'development_buffer_width_m', 20.0,
        'buffer_width_is_official', false,
        'source_axis_status', 'estimated',
        'eligible_for_official_reporting', false
    )
FROM target_segment target
CROSS JOIN prepared_zones zone
ON CONFLICT (road_segment_id, zone_type) DO NOTHING;

COMMIT;
