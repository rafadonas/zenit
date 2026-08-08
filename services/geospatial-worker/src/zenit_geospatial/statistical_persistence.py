"""Auditable persistence of prepared Sentinel Statistical API results."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from zenit_geospatial.sentinel_statistics import PROCESSING_VERSION, SentinelStatistic

SATELLITE_RULE_VERSION = "satellite-quality-2026-08-07.1"


@dataclass(frozen=True, slots=True)
class PersistedStatisticalAnalysis:
    analysis_run_id: UUID
    created: bool


def statistical_idempotency_key(
    scene_id: UUID,
    segment_zone_id: UUID,
    geometry_hash: str,
    statistic: SentinelStatistic,
) -> str:
    canonical = {
        "geometry_hash": geometry_hash,
        "interval_from": statistic.interval_from.isoformat(),
        "interval_to": statistic.interval_to.isoformat(),
        "processor_version": PROCESSING_VERSION,
        "rule_version": SATELLITE_RULE_VERSION,
        "scene_id": str(scene_id),
        "segment_zone_id": str(segment_zone_id),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def prepared_explanation(
    statistic: SentinelStatistic,
    *,
    geometry_hash: str,
) -> dict[str, Any]:
    return {
        "quality_status": statistic.quality_status,
        "valid_pixel_ratio": statistic.valid_pixel_ratio,
        "sample_count": statistic.sample_count,
        "no_data_count": statistic.no_data_count,
        "ndvi_std": statistic.ndvi_std,
        "ndvi_percentiles": {
            "p25": statistic.ndvi_p25,
            "p50": statistic.ndvi_p50,
            "p75": statistic.ndvi_p75,
        },
        "geometry_hash": geometry_hash,
        "input_data_status": "prepared",
        "result_data_status": "inconclusive",
        "source_link_role": "catalog_prefilter_candidate",
        "statistical_api_mosaic": True,
        "reasons": [
            "The AOI is derived from an estimated axis with a non-official development buffer.",
            "Statistical API quality does not establish vegetation height.",
            "A field inspection and validated corridor geometry are required.",
        ],
    }


class PostgresStatisticalAnalysisRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def register_prepared(
        self,
        *,
        scene_id: UUID,
        segment_zone_id: UUID,
        geometry_hash: str,
        statistic: SentinelStatistic,
    ) -> PersistedStatisticalAnalysis:
        key = statistical_idempotency_key(
            scene_id,
            segment_zone_id,
            geometry_hash,
            statistic,
        )
        parameters = {
            "processing_version": PROCESSING_VERSION,
            "quality_rule_version": SATELLITE_RULE_VERSION,
            "interval": {
                "from": statistic.interval_from.isoformat(),
                "to": statistic.interval_to.isoformat(),
            },
            "geometry_hash": geometry_hash,
            "input_data_status": "prepared",
            "statistical_api_mosaic": True,
        }
        insert_run = """
            INSERT INTO analysis_run (
                satellite_scene_id,
                rule_version,
                processor_version,
                idempotency_key,
                status,
                parameters
            )
            VALUES (%s, %s, %s, %s, 'running', %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id
        """
        find_run = "SELECT id FROM analysis_run WHERE idempotency_key = %s"
        insert_result = """
            INSERT INTO vegetation_analysis (
                analysis_run_id,
                segment_zone_id,
                mean_ndvi,
                valid_pixel_percent,
                observed_height_cm,
                height_data_status,
                conclusion,
                recommendation,
                confidence_band,
                explanation,
                requires_human_approval,
                eligible_for_official_reporting
            )
            VALUES (
                %s, %s, %s, %s, NULL, NULL, 'inconclusive', 'inspect', 'low', %s, true, false
            )
        """
        complete_run = """
            UPDATE analysis_run
            SET status = 'completed', completed_at = now()
            WHERE id = %s
        """
        valid_pixel_percent = (
            statistic.valid_pixel_ratio * 100
            if statistic.valid_pixel_ratio is not None
            else 0.0
        )
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                insert_run,
                (
                    scene_id,
                    SATELLITE_RULE_VERSION,
                    PROCESSING_VERSION,
                    key,
                    Jsonb(parameters),
                ),
            )
            inserted = cursor.fetchone()
            if inserted is None:
                cursor.execute(find_run, (key,))
                existing = cursor.fetchone()
                if existing is None:
                    raise RuntimeError("analysis run disappeared during idempotent registration")
                return PersistedStatisticalAnalysis(analysis_run_id=existing[0], created=False)

            run_id = inserted[0]
            cursor.execute(
                insert_result,
                (
                    run_id,
                    segment_zone_id,
                    statistic.mean_ndvi,
                    valid_pixel_percent,
                    Jsonb(prepared_explanation(statistic, geometry_hash=geometry_hash)),
                ),
            )
            cursor.execute(complete_run, (run_id,))
            return PersistedStatisticalAnalysis(analysis_run_id=run_id, created=True)
