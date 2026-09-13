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


class MultiPolygonGeometry(BaseModel):
    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: list[list[list[list[float]]]]


class VegetationMapProperties(BaseModel):
    polygon_id: str
    source_index: int
    road_code: str
    nearest_segment_id: str
    segment_index: int
    vegetation_class: Literal["N1", "N2", "N3", "X", "unknown"]
    reference_date: str
    version_label: str
    equipment_class: str
    original_geometry_valid: bool
    data_status: Literal["historical"] = "historical"
    mapping_status: Literal["inferred_needs_validation"] = "inferred_needs_validation"
    eligible_for_operations: Literal[False] = False


class VegetationMapFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: MultiPolygonGeometry
    properties: VegetationMapProperties


class VegetationMapFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[VegetationMapFeature]
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    min_longitude: float
    min_latitude: float
    max_longitude: float
    max_latitude: float


class SegmentReader(Protocol):
    async def by_bbox(self, road_code: str, bbox: BoundingBox) -> SegmentFeatureCollection: ...

    async def vegetation_by_bbox(
        self,
        road_code: str,
        bbox: BoundingBox,
    ) -> VegetationMapFeatureCollection: ...


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

    async def vegetation_by_bbox(
        self,
        road_code: str,
        bbox: BoundingBox,
    ) -> VegetationMapFeatureCollection:
        query = """
            WITH latest_version AS (
                SELECT version_label, reference_date
                FROM staging_vegetation_observation
                ORDER BY version_label DESC, reference_date DESC
                LIMIT 1
            ), station_state AS (
                SELECT
                    observation.station_meter,
                    CASE max(
                        CASE observation.vegetation_class
                            WHEN 'N3' THEN 3 WHEN 'N2' THEN 2 WHEN 'N1' THEN 1 ELSE 0
                        END
                    )
                        WHEN 3 THEN 'N3' WHEN 2 THEN 'N2' WHEN 1 THEN 'N1'
                        WHEN 0 THEN 'X' ELSE 'unknown'
                    END AS vegetation_class
                FROM staging_vegetation_observation observation
                JOIN latest_version latest
                  ON latest.version_label = observation.version_label
                 AND latest.reference_date = observation.reference_date
                GROUP BY observation.station_meter
            ), prepared_polygon AS MATERIALIZED (
                SELECT
                    polygon.*,
                    ST_Multi(ST_CollectionExtract(ST_MakeValid(polygon.original_geometry), 3))
                        AS display_geometry
                FROM staging_mowing_polygon polygon
            )
            SELECT
                polygon.id::text,
                polygon.source_index,
                polygon.equipment_class,
                ST_IsValid(polygon.original_geometry),
                nearest.segment_id,
                nearest.segment_index,
                COALESCE(state.vegetation_class, 'unknown'),
                latest.reference_date::text,
                latest.version_label,
                ST_AsGeoJSON(polygon.display_geometry, 7)::jsonb
            FROM prepared_polygon polygon
            CROSS JOIN latest_version latest
            CROSS JOIN LATERAL (
                SELECT
                    segment.id::text AS segment_id,
                    segment.segment_index,
                    segment.start_distance_m
                FROM road_segment segment
                JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
                JOIN road ON road.id = axis.road_id
                WHERE road.code = %s
                ORDER BY segment.metric_geometry <->
                    ST_Transform(ST_PointOnSurface(polygon.display_geometry), 31983)
                LIMIT 1
            ) nearest
            LEFT JOIN station_state state
              ON state.station_meter = round(nearest.start_distance_m / 500.0) * 500
            WHERE NOT ST_IsEmpty(polygon.display_geometry)
              AND polygon.display_geometry && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
            ORDER BY polygon.source_index
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
            VegetationMapFeature(
                geometry=MultiPolygonGeometry.model_validate(row[9]),
                properties=VegetationMapProperties(
                    polygon_id=row[0],
                    source_index=row[1],
                    road_code=road_code,
                    nearest_segment_id=row[4],
                    segment_index=row[5],
                    vegetation_class=row[6],
                    reference_date=row[7],
                    version_label=row[8],
                    equipment_class=row[2],
                    original_geometry_valid=row[3],
                ),
            )
            for row in rows
        ]
        return VegetationMapFeatureCollection(
            features=features,
            metadata={
                "road_code": road_code,
                "output_crs": "EPSG:4326",
                "reference_date": rows[0][7] if rows else "2025-03-28",
                "data_status": "historical",
                "mapping_status": "inferred_needs_validation",
                "classification_rule": "N1 < 10 cm; N2 10-30 cm; N3 > 30 cm",
                "mapping_method": (
                    "polygon nearest to estimated 100 m segment; conservative highest class "
                    "from the nearest 500 m station"
                ),
                "warning": (
                    "Historical reference from 2025-03-28; not current vegetation condition "
                    "and not eligible for operations"
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


@router.get(
    "/{road_code}/vegetation-map",
    response_model=VegetationMapFeatureCollection,
)
async def list_vegetation_map(
    road_code: str,
    min_lon: Annotated[float, Query(ge=-180, le=180)],
    min_lat: Annotated[float, Query(ge=-90, le=90)],
    max_lon: Annotated[float, Query(ge=-180, le=180)],
    max_lat: Annotated[float, Query(ge=-90, le=90)],
    reader: Annotated[SegmentReader, Depends(get_segment_reader)],
) -> VegetationMapFeatureCollection:
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=422, detail="Bounding box minimums must be below maximums")
    return await reader.vegetation_by_bbox(
        road_code,
        BoundingBox(
            min_longitude=min_lon,
            min_latitude=min_lat,
            max_longitude=max_lon,
            max_latitude=max_lat,
        ),
    )
