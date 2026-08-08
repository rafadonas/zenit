"""Idempotent persistence for normalized satellite acquisition metadata."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from zenit_geospatial.satellite_providers import Acquisition


@dataclass(frozen=True, slots=True)
class CatalogedScene:
    id: UUID
    created: bool
    cache_status: str


def catalog_checksum(acquisition: Acquisition) -> str:
    """Hash the normalized first-discovery snapshot without credentials."""

    canonical = {
        "assets": dict(sorted(acquisition.assets.items())),
        "bbox": acquisition.bbox,
        "cloud_cover_percent": acquisition.cloud_cover_percent,
        "collection": acquisition.collection,
        "external_scene_id": acquisition.external_scene_id,
        "geometry": acquisition.geometry,
        "provider": acquisition.provider,
        "sensor": acquisition.sensor,
        "source_metadata": acquisition.source_metadata,
        "acquired_at": acquisition.acquired_at.isoformat(),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def catalog_metadata(acquisition: Acquisition) -> dict[str, Any]:
    return {
        "catalog_only": True,
        "assets": dict(acquisition.assets),
        "bbox": acquisition.bbox,
        "source_properties": dict(acquisition.source_metadata),
    }


class PostgresSatelliteCatalog:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def register(self, acquisition: Acquisition, discovered_at: datetime) -> CatalogedScene:
        if discovered_at.tzinfo is None:
            raise ValueError("discovered_at must be timezone-aware")
        geometry_json = (
            json.dumps(acquisition.geometry, separators=(",", ":"))
            if acquisition.geometry is not None
            else None
        )
        insert = """
            INSERT INTO satellite_scene (
                provider,
                external_scene_id,
                collection,
                sensor,
                acquired_at,
                discovered_at,
                cached_at,
                cache_status,
                footprint,
                cloud_cover_percent,
                quality_status,
                data_status,
                catalog_checksum_sha256,
                metadata
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, NULL, 'discovered',
                CASE
                    WHEN %s::text IS NULL THEN NULL
                    ELSE ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s::text), 4326))
                END,
                %s, 'pending', 'real', %s, %s
            )
            ON CONFLICT (provider, external_scene_id) DO NOTHING
            RETURNING id, cache_status
        """
        select_existing = """
            SELECT id, cache_status
            FROM satellite_scene
            WHERE provider = %s AND external_scene_id = %s
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                insert,
                (
                    acquisition.provider,
                    acquisition.external_scene_id,
                    acquisition.collection,
                    acquisition.sensor,
                    acquisition.acquired_at,
                    discovered_at,
                    geometry_json,
                    geometry_json,
                    acquisition.cloud_cover_percent,
                    catalog_checksum(acquisition),
                    Jsonb(catalog_metadata(acquisition)),
                ),
            )
            inserted = cursor.fetchone()
            if inserted is not None:
                return CatalogedScene(id=inserted[0], created=True, cache_status=inserted[1])
            cursor.execute(
                select_existing,
                (acquisition.provider, acquisition.external_scene_id),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise RuntimeError("satellite scene disappeared during idempotent registration")
            return CatalogedScene(id=existing[0], created=False, cache_status=existing[1])
