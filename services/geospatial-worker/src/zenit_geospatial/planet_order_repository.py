"""Postgres lineage for a bounded Planet Order and its downloaded assets."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True, slots=True)
class PreparedSegmentAoi:
    segment_id: UUID
    geometry: dict[str, Any]
    area_m2: float
    data_status: str
    eligible_for_operations: bool


@dataclass(frozen=True, slots=True)
class ExistingPlanetOrder:
    id: UUID
    external_order_id: str
    order_state: str
    downloaded_bytes: int


class PostgresPlanetOrderRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def prepared_segment_aoi(
        self,
        *,
        road_code: str,
        segment_index: int,
        buffer_m: float,
    ) -> PreparedSegmentAoi:
        if buffer_m < 0 or buffer_m > 100:
            raise ValueError("buffer_m must be between 0 and 100")
        query = """
            SELECT
                segment.id,
                ST_AsGeoJSON(ST_Transform(ST_Buffer(segment.metric_geometry, %s), 4326)),
                ST_Area(ST_Transform(ST_Buffer(segment.metric_geometry, %s), 4326)::geography),
                segment.data_status,
                segment.eligible_for_operations
            FROM road_segment segment
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            WHERE road.code = %s
              AND segment.segment_index = %s
              AND segment.data_status = 'estimated'
              AND NOT segment.eligible_for_operations
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (buffer_m, buffer_m, road_code, segment_index))
            row = cursor.fetchone()
        if row is None:
            raise LookupError("prepared estimated segment was not found")
        geometry = json.loads(row[1])
        if not isinstance(geometry, dict):
            raise RuntimeError("prepared segment AOI is not a GeoJSON object")
        return PreparedSegmentAoi(
            segment_id=row[0],
            geometry=geometry,
            area_m2=float(row[2]),
            data_status=row[3],
            eligible_for_operations=bool(row[4]),
        )

    def find_by_request_checksum(self, checksum: str) -> ExistingPlanetOrder | None:
        query = """
            SELECT id, external_order_id, order_state, downloaded_bytes
            FROM planet_order
            WHERE request_checksum_sha256 = %s
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (checksum,))
            row = cursor.fetchone()
        if row is None:
            return None
        return ExistingPlanetOrder(
            id=row[0],
            external_order_id=row[1],
            order_state=row[2],
            downloaded_bytes=int(row[3]),
        )

    def create_order(
        self,
        *,
        external_order_id: str,
        order_name: str,
        item_ids: list[str],
        aoi: Mapping[str, Any],
        aoi_area_m2: float,
        max_bytes: int,
        license_scope: str,
        retention_days: int,
        destination_bucket: str,
        destination_prefix: str,
        request_checksum: str,
        response_metadata: Mapping[str, Any],
        order_state: str,
    ) -> UUID:
        query = """
            INSERT INTO planet_order (
                external_order_id, order_name, source_type, item_type, item_ids,
                product_bundle, aoi, aoi_area_m2, max_bytes, license_scope,
                retention_days, destination_bucket, destination_prefix,
                request_checksum_sha256, order_state, response_metadata
            )
            VALUES (
                %s, %s, 'scenes', 'PSScene', %s, 'analytic_udm2',
                ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            RETURNING id
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    external_order_id,
                    order_name,
                    Jsonb(item_ids),
                    json.dumps(aoi, separators=(",", ":")),
                    aoi_area_m2,
                    max_bytes,
                    license_scope,
                    retention_days,
                    destination_bucket,
                    destination_prefix,
                    request_checksum,
                    order_state,
                    Jsonb(dict(response_metadata)),
                ),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Planet Order was not persisted")
        return row[0]

    def record_event(
        self,
        *,
        order_id: UUID,
        event_type: str,
        order_state: str,
        details: Mapping[str, Any],
    ) -> None:
        query = """
            INSERT INTO planet_order_event (planet_order_id, event_type, order_state, details)
            VALUES (%s, %s, %s, %s)
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (order_id, event_type, order_state, Jsonb(dict(details))))

    def update_state(
        self,
        *,
        order_id: UUID,
        order_state: str,
        response_metadata: Mapping[str, Any],
        downloaded_bytes: int,
        completed_at: datetime | None = None,
    ) -> None:
        query = """
            UPDATE planet_order
            SET order_state = %s,
                response_metadata = %s,
                downloaded_bytes = %s,
                completed_at = %s
            WHERE id = %s
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    order_state,
                    Jsonb(dict(response_metadata)),
                    downloaded_bytes,
                    completed_at,
                    order_id,
                ),
            )
            if cursor.rowcount != 1:
                raise LookupError("Planet Order lineage row was not found")

    def register_asset(
        self,
        *,
        order_id: UUID,
        scene_id: UUID,
        asset_role: str,
        storage_uri: str,
        checksum_sha256: str,
        media_type: str,
        storage_version_id: str | None = None,
        size_bytes: int | None = None,
    ) -> None:
        query = """
            INSERT INTO satellite_asset (
                satellite_scene_id, asset_role, storage_uri, checksum_sha256,
                media_type, source_order_id, storage_version_id, size_bytes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (satellite_scene_id, asset_role, checksum_sha256) DO NOTHING
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    scene_id,
                    asset_role,
                    storage_uri,
                    checksum_sha256,
                    media_type,
                    order_id,
                    storage_version_id,
                    size_bytes,
                ),
            )

    def mark_scene_cached(self, *, scene_id: UUID, cached_at: datetime) -> None:
        if cached_at.tzinfo is None:
            raise ValueError("cached_at must be timezone-aware")
        query = """
            UPDATE satellite_scene
            SET cache_status = 'cached', cached_at = %s
            WHERE id = %s
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query, (cached_at, scene_id))
            if cursor.rowcount != 1:
                raise LookupError("Planet scene lineage row was not found")
