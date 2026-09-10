#!/usr/bin/env python3
"""Seed demonstrative prepared work orders for local development."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://zenit:change_me@localhost:5432/zenit",
).replace("postgresql+psycopg://", "postgresql://", 1)

def main() -> None:
    now = datetime.now(UTC)
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Get road
            cur.execute("SELECT id FROM road WHERE code = 'SP021'")
            road_row = cur.fetchone()
            if not road_row:
                raise RuntimeError("Road SP021 not found in DB.")
            road_id = road_row[0]

            # 2. Get user
            cur.execute("SELECT id FROM app_user WHERE email = 'manager@example.com'")
            user_row = cur.fetchone()
            if not user_row:
                raise RuntimeError("User manager@example.com not found.")
            user_id = user_row[0]

            # 3. Get segment zone
            cur.execute(
                """
                SELECT sz.id, rs.segment_index, sz.zone_type, rs.metric_geometry
                FROM segment_zone sz
                JOIN road_segment rs ON rs.id = sz.road_segment_id
                JOIN road_axis_candidate rac ON rac.id = rs.road_axis_candidate_id
                WHERE rac.road_id = %s
                LIMIT 1
                """,
                (road_id,),
            )
            zone_row = cur.fetchone()
            if not zone_row:
                cur.execute(
                    """
                    SELECT rs.id, rs.metric_geometry
                    FROM road_segment rs
                    JOIN road_axis_candidate rac ON rac.id = rs.road_axis_candidate_id
                    WHERE rac.road_id = %s
                    LIMIT 1
                    """,
                    (road_id,),
                )
                segment_id, metric_geom = cur.fetchone()
                cur.execute(
                    """
                    INSERT INTO segment_zone (
                        road_segment_id, zone_type, threshold_cm, metric_geometry, data_status
                    )
                    VALUES (%s, 'left', 30.00, %s, 'prepared')
                    RETURNING id
                    """,
                    (segment_id, metric_geom),
                )
                zone_id = cur.fetchone()[0]
            else:
                zone_id = zone_row[0]

            # Check existing work order
            cur.execute("SELECT wo.id FROM work_order wo WHERE wo.segment_zone_id = %s", (zone_id,))
            existing_wo = cur.fetchone()
            if existing_wo:
                print(f"Work order already exists for zone {zone_id}: {existing_wo[0]}")
                return

            # 4. Create satellite scene & analysis run
            scene_id = uuid4()
            scene_checksum = hashlib.sha256(f"scene-{scene_id}".encode()).hexdigest()
            cur.execute(
                """
                INSERT INTO satellite_scene (
                    id, provider, external_scene_id, sensor, collection,
                    catalog_checksum_sha256, acquired_at
                ) VALUES (
                    %s, 'sentinel', %s, 'sentinel-2', 'sentinel-2-l2a', %s, %s
                )
                ON CONFLICT (provider, external_scene_id)
                DO UPDATE SET acquired_at = EXCLUDED.acquired_at
                RETURNING id
                """,
                (scene_id, f"scene-{scene_id}", scene_checksum, now),
            )
            scene_id = cur.fetchone()[0]

            run_id = uuid4()
            run_idem = hashlib.sha256(f"run-{run_id}".encode()).hexdigest()
            cur.execute(
                """
                INSERT INTO analysis_run (
                    id, satellite_scene_id, rule_version, processor_version,
                    idempotency_key, status, completed_at
                ) VALUES (
                    %s, %s, 'v1', 'v1', %s, 'completed', %s
                )
                """,
                (run_id, scene_id, run_idem, now),
            )

            # 5. Create vegetation_analysis
            analysis_id = uuid4()
            cur.execute(
                """
                INSERT INTO vegetation_analysis (
                    id, analysis_run_id, segment_zone_id, valid_pixel_percent,
                    conclusion, recommendation, confidence_band, explanation,
                    requires_human_approval, eligible_for_official_reporting
                ) VALUES (
                    %s, %s, %s, 85.00,
                    'inconclusive', 'inspect', 'low', %s::jsonb,
                    true, false
                )
                """,
                (
                    analysis_id,
                    run_id,
                    zone_id,
                    json.dumps({"reasons": ["Low confidence requires inspection"]}),
                ),
            )

            # 6. Create recommendation_review
            review_id = uuid4()
            review_idem = hashlib.sha256(f"rev-{review_id}".encode()).hexdigest()
            cur.execute(
                """
                INSERT INTO recommendation_review (
                    id, vegetation_analysis_id, idempotency_key, decision,
                    reviewer_subject, reviewer_user_id, review_policy_id,
                    source_channel, reviewed_at
                ) VALUES (
                    %s, %s, %s, 'accepted',
                    %s, %s, '90000000-0000-4000-8000-000000000001',
                    'dashboard', %s
                )
                """,
                (review_id, analysis_id, review_idem, str(user_id), user_id, now),
            )

            # 7. Create work_order
            wo_id = uuid4()
            wo_idem = hashlib.sha256(f"wo-{wo_id}".encode()).hexdigest()
            cur.execute(
                """
                INSERT INTO work_order (
                    id, source_review_id, segment_zone_id, creation_policy_id, created_by_user_id,
                    idempotency_key, order_type, status, version, planning_rationale, data_status,
                    authorizes_field_work, eligible_for_field_execution,
                    eligible_for_official_reporting,
                    order_metadata
                ) VALUES (
                    %s, %s, %s, '91000000-0000-4000-8000-000000000001', %s,
                    %s, 'inspection', 'prepared', 1, 'Inspeção preventiva de borda', 'prepared',
                    false, false, false, %s::jsonb
                )
                """,
                (
                    wo_id,
                    review_id,
                    zone_id,
                    user_id,
                    wo_idem,
                    json.dumps({"actor_role": "manager", "authorizes_field_work": False}),
                ),
            )

            # 8. Create 3 work_order_planned_points
            fractions = [1.0/6.0, 0.5, 5.0/6.0]
            for seq, frac in enumerate(fractions, start=1):
                pt_id = uuid4()
                cur.execute(
                    """
                    INSERT INTO work_order_planned_point (
                        id, work_order_id, sequence, position_fraction, planned_geometry,
                        planning_method, data_status, eligible_for_field_execution
                    )
                    SELECT
                        %s, %s, %s, %s,
                        ST_LineInterpolatePoint(segment.metric_geometry, %s),
                        'segment_centerline_fraction', segment.data_status, false
                    FROM segment_zone zone
                    JOIN road_segment segment ON segment.id = zone.road_segment_id
                    WHERE zone.id = %s
                    """,
                    (pt_id, wo_id, seq, frac, frac, zone_id),
                )

        conn.commit()
        print(f"SEED COMPLETED SUCCESSFULLY: Created work_order {wo_id}")

if __name__ == "__main__":
    main()
