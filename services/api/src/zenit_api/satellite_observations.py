from __future__ import annotations

from typing import Annotated, Any, Literal, Protocol
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from zenit_api.config import get_settings


class SatelliteAssetEvidence(BaseModel):
    role: str
    media_type: str
    checksum_sha256: str = Field(min_length=64, max_length=64)


class SatelliteObservation(BaseModel):
    analysis_run_id: UUID
    scene_id: UUID
    provider: str
    collection: str
    sensor: Literal["sentinel-2", "cbers-4a"]
    acquired_at: str
    cache_status: Literal["discovered", "partially_cached", "cached"]
    scene_data_status: str
    zone_type: Literal["left", "right", "median", "special"]
    zone_data_status: str
    mean_ndvi: float | None
    valid_pixel_percent: float
    conclusion: Literal["conclusive", "inconclusive"]
    recommendation: Literal["monitor", "inspect", "mowing_review"]
    confidence_band: Literal["low", "medium", "high"]
    requires_human_approval: bool
    eligible_for_official_reporting: bool
    rule_version: str
    processor_version: str
    explanation: dict[str, Any]
    assets: list[SatelliteAssetEvidence]


class SatelliteObservationCollection(BaseModel):
    items: list[SatelliteObservation]
    metadata: dict[str, Any]


class SatelliteObservationReader(Protocol):
    async def by_segment(
        self, segment_id: UUID, *, limit: int
    ) -> SatelliteObservationCollection: ...


class PostgresSatelliteObservationRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def by_segment(
        self, segment_id: UUID, *, limit: int
    ) -> SatelliteObservationCollection:
        query = """
            SELECT
                analysis.id,
                scene.id,
                scene.provider,
                scene.collection,
                scene.sensor,
                scene.acquired_at,
                scene.cache_status,
                scene.data_status,
                zone.zone_type,
                zone.data_status,
                result.mean_ndvi,
                result.valid_pixel_percent,
                result.conclusion,
                result.recommendation,
                result.confidence_band,
                result.requires_human_approval,
                result.eligible_for_official_reporting,
                analysis.rule_version,
                analysis.processor_version,
                result.explanation,
                COALESCE(assets.items, '[]'::jsonb)
            FROM vegetation_analysis result
            JOIN analysis_run analysis ON analysis.id = result.analysis_run_id
            JOIN satellite_scene scene ON scene.id = analysis.satellite_scene_id
            JOIN segment_zone zone ON zone.id = result.segment_zone_id
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'role', asset.asset_role,
                        'media_type', asset.media_type,
                        'checksum_sha256', asset.checksum_sha256
                    ) ORDER BY asset.asset_role
                ) AS items
                FROM satellite_asset asset
                WHERE asset.satellite_scene_id = scene.id
            ) assets ON true
            WHERE zone.road_segment_id = %s
            ORDER BY scene.acquired_at DESC, result.created_at DESC
            LIMIT %s
        """
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(query, (segment_id, limit))
            rows = await cursor.fetchall()
        items = [
            SatelliteObservation(
                analysis_run_id=row[0],
                scene_id=row[1],
                provider=row[2],
                collection=row[3],
                sensor=row[4],
                acquired_at=row[5].isoformat(),
                cache_status=row[6],
                scene_data_status=row[7],
                zone_type=row[8],
                zone_data_status=row[9],
                mean_ndvi=float(row[10]) if row[10] is not None else None,
                valid_pixel_percent=float(row[11]),
                conclusion=row[12],
                recommendation=row[13],
                confidence_band=row[14],
                requires_human_approval=row[15],
                eligible_for_official_reporting=row[16],
                rule_version=row[17],
                processor_version=row[18],
                explanation=row[19],
                assets=[SatelliteAssetEvidence.model_validate(asset) for asset in row[20]],
            )
            for row in rows
        ]
        return SatelliteObservationCollection(
            items=items,
            metadata={
                "segment_id": str(segment_id),
                "result_count": len(items),
                "warning": (
                    "Satellite quality is not vegetation height or authorization for mowing."
                ),
            },
        )


async def get_satellite_observation_reader() -> SatelliteObservationReader:
    return PostgresSatelliteObservationRepository(get_settings().database_url)


router = APIRouter(prefix="/v1/segments", tags=["satellite-observations"])


@router.get(
    "/{segment_id}/satellite-observations",
    response_model=SatelliteObservationCollection,
)
async def list_satellite_observations(
    segment_id: UUID,
    reader: Annotated[
        SatelliteObservationReader, Depends(get_satellite_observation_reader)
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SatelliteObservationCollection:
    return await reader.by_segment(segment_id, limit=limit)
