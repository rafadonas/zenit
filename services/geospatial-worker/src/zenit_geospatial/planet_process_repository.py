"""Database access for the offline pilot processing (PLANET-008).

Only assets whose most recent integrity audit says ``verified`` may be processed,
so a divergent or missing object can never reach a statistic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from zenit_geospatial.planet_process import PROCESSOR_VERSION, RULE_VERSION, ZoneStatistics


@dataclass(frozen=True, slots=True)
class CachedAsset:
    id: UUID
    asset_role: str
    storage_uri: str
    checksum_sha256: str
    storage_version_id: str | None
    verification_status: str | None


@dataclass(frozen=True, slots=True)
class CachedScene:
    id: UUID
    external_scene_id: str
    assets: tuple[CachedAsset, ...]

    def asset(self, role_prefix: str) -> CachedAsset:
        matches = [item for item in self.assets if item.asset_role.startswith(role_prefix)]
        if not matches:
            raise LookupError(f"cached scene has no {role_prefix!r} asset")
        if len(matches) > 1:
            raise LookupError(f"cached scene has more than one {role_prefix!r} asset")
        return matches[0]


@dataclass(frozen=True, slots=True)
class PilotZone:
    id: UUID
    segment_index: int
    zone_type: str
    geometry: dict[str, Any]
    data_status: str
    eligible_for_operations: bool


class PostgresPilotProcessing:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def scene(self, external_scene_id: str) -> CachedScene:
        query = """
            SELECT scene.id, asset.id, asset.asset_role, asset.storage_uri,
                   asset.checksum_sha256, asset.storage_version_id,
                   (
                       SELECT status FROM satellite_asset_verification audit
                       WHERE audit.satellite_asset_id = asset.id
                       ORDER BY audit.checked_at DESC
                       LIMIT 1
                   )
            FROM satellite_scene scene
            JOIN satellite_asset asset ON asset.satellite_scene_id = scene.id
            WHERE scene.external_scene_id = %s AND scene.provider = 'planet'
            ORDER BY asset.asset_role
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (external_scene_id,))
            rows = cursor.fetchall()
        if not rows:
            raise LookupError(f"no cached Planet assets for scene {external_scene_id!r}")
        return CachedScene(
            id=rows[0][0],
            external_scene_id=external_scene_id,
            assets=tuple(
                CachedAsset(
                    id=row[1],
                    asset_role=row[2],
                    storage_uri=row[3],
                    checksum_sha256=row[4],
                    storage_version_id=row[5],
                    verification_status=row[6],
                )
                for row in rows
            ),
        )

    def pilot_zones(
        self, *, road_code: str, from_segment: int, to_segment: int
    ) -> tuple[PilotZone, ...]:
        query = """
            SELECT zone.id, segment.segment_index, zone.zone_type,
                   ST_AsGeoJSON(zone.metric_geometry), zone.data_status,
                   zone.eligible_for_operations
            FROM segment_zone zone
            JOIN road_segment segment ON segment.id = zone.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            WHERE road.code = %s
              AND segment.segment_index BETWEEN %s AND %s
              AND zone.metric_geometry IS NOT NULL
            ORDER BY segment.segment_index, zone.zone_type
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (road_code, from_segment, to_segment))
            rows = cursor.fetchall()
        return tuple(
            PilotZone(
                id=row[0],
                segment_index=row[1],
                zone_type=row[2],
                geometry=json.loads(row[3]),
                data_status=row[4],
                eligible_for_operations=bool(row[5]),
            )
            for row in rows
        )

    def persist(
        self,
        *,
        scene_id: UUID,
        statistics: ZoneStatistics,
        idempotency_key: str,
        parameters: dict[str, Any],
        explanation: dict[str, Any],
    ) -> bool:
        """Append one zone result; repeating the same inputs changes nothing."""
        insert_run = """
            INSERT INTO analysis_run (
                satellite_scene_id, rule_version, processor_version, idempotency_key,
                status, parameters
            )
            VALUES (%s, %s, %s, %s, 'running', %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id
        """
        find_run = "SELECT id FROM analysis_run WHERE idempotency_key = %s"
        insert_result = """
            INSERT INTO vegetation_analysis (
                analysis_run_id, segment_zone_id, mean_ndvi, valid_pixel_percent,
                observed_height_cm, height_data_status, conclusion, recommendation,
                confidence_band, explanation, requires_human_approval,
                eligible_for_official_reporting
            )
            VALUES (%s, %s, %s, %s, NULL, NULL, 'inconclusive', 'inspect', 'low', %s, true, false)
            ON CONFLICT (analysis_run_id, segment_zone_id) DO NOTHING
        """
        complete_run = """
            UPDATE analysis_run SET status = 'completed', completed_at = now()
            WHERE id = %s AND status = 'running'
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                insert_run,
                (
                    scene_id,
                    RULE_VERSION,
                    PROCESSOR_VERSION,
                    idempotency_key,
                    Jsonb(parameters),
                ),
            )
            row = cursor.fetchone()
            created = row is not None
            if row is None:
                cursor.execute(find_run, (idempotency_key,))
                row = cursor.fetchone()
            run_id = row[0]
            cursor.execute(
                insert_result,
                (
                    run_id,
                    statistics.segment_zone_id,
                    statistics.mean_ndvi,
                    statistics.valid_pixel_percent,
                    Jsonb(explanation),
                ),
            )
            cursor.execute(complete_run, (run_id,))
        return created
