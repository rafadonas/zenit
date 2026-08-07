from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from zenit_api.config import get_settings


class LineStringGeometry(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]


class SegmentProperties(BaseModel):
    segment_id: str
    segment_index: int
    start_distance_m: float
    end_distance_m: float
    data_status: str
    validation_status: str
    eligible_for_operations: bool


class SegmentFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: LineStringGeometry
    properties: SegmentProperties


class SegmentFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[SegmentFeature]
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    min_longitude: float
    min_latitude: float
    max_longitude: float
    max_latitude: float


class SegmentReader(Protocol):
    async def by_bbox(self, road_code: str, bbox: BoundingBox) -> SegmentFeatureCollection: ...


class PostgresSegmentRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def by_bbox(self, road_code: str, bbox: BoundingBox) -> SegmentFeatureCollection:
        query = """
            SELECT
                segment.id::text,
                segment.segment_index,
                segment.start_distance_m,
                segment.end_distance_m,
                segment.data_status,
                axis.validation_status,
                segment.eligible_for_operations,
                ST_AsGeoJSON(ST_Transform(segment.metric_geometry, 4326), 7)::jsonb
            FROM road_segment segment
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            WHERE road.code = %s
              AND segment.metric_geometry && ST_Transform(
                    ST_MakeEnvelope(%s, %s, %s, %s, 4326),
                    31983
                  )
            ORDER BY segment.segment_index
            LIMIT 2000
        """
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                query,
                (
                    road_code,
                    bbox.min_longitude,
                    bbox.min_latitude,
                    bbox.max_longitude,
                    bbox.max_latitude,
                ),
            )
            rows = await cursor.fetchall()
        features = [
            SegmentFeature(
                geometry=LineStringGeometry.model_validate(row[7]),
                properties=SegmentProperties(
                    segment_id=row[0],
                    segment_index=row[1],
                    start_distance_m=row[2],
                    end_distance_m=row[3],
                    data_status=row[4],
                    validation_status=row[5],
                    eligible_for_operations=row[6],
                ),
            )
            for row in rows
        ]
        return SegmentFeatureCollection(
            features=features,
            metadata={
                "road_code": road_code,
                "metric_crs": "EPSG:31983",
                "output_crs": "EPSG:4326",
                "operational_warning": (
                    "Estimated marker-derived axis; not eligible for operations"
                ),
            },
        )


async def get_segment_reader() -> SegmentReader:
    return PostgresSegmentRepository(get_settings().database_url)


router = APIRouter(prefix="/v1/roads", tags=["segments"])


@router.get("/{road_code}/segments", response_model=SegmentFeatureCollection)
async def list_segments(
    road_code: str,
    min_lon: Annotated[float, Query(ge=-180, le=180)],
    min_lat: Annotated[float, Query(ge=-90, le=90)],
    max_lon: Annotated[float, Query(ge=-180, le=180)],
    max_lat: Annotated[float, Query(ge=-90, le=90)],
    reader: Annotated[SegmentReader, Depends(get_segment_reader)],
) -> SegmentFeatureCollection:
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=422, detail="Bounding box minimums must be below maximums")
    return await reader.by_bbox(
        road_code,
        BoundingBox(
            min_longitude=min_lon,
            min_latitude=min_lat,
            max_longitude=max_lon,
            max_latitude=max_lat,
        ),
    )
