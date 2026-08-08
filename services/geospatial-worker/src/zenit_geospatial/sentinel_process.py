"""Small Sentinel Process API NDVI crops with contributing-scene metadata."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg

from zenit_geospatial.satellite_http import CopernicusTokenProvider, UrllibJsonTransport

SENTINEL_PROCESS_URL = "https://sh.dataspace.copernicus.eu/process/v1"
PROCESS_RASTER_VERSION = "sentinel-ndvi-crop-v1"

PROCESS_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
    output: { id: "default", bands: 1, sampleType: "FLOAT32", nodataValue: -9999 },
    mosaicking: "TILE"
  };
}
function valid(s) {
  const invalid = [0, 1, 3, 6, 7, 8, 9, 10, 11];
  return s.dataMask === 1 && !invalid.includes(s.SCL) && (s.B08 + s.B04) !== 0;
}
function evaluatePixel(samples) {
  for (let i = 0; i < samples.length; i++) {
    const s = samples[i];
    if (valid(s)) return [(s.B08 - s.B04) / (s.B08 + s.B04)];
  }
  return [-9999];
}
function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {
  outputMetadata.userData = {
    scenes: scenes,
    serviceVersion: inputMetadata.serviceVersion,
    processingVersion: "sentinel-ndvi-crop-v1"
  };
}
"""


@dataclass(frozen=True, slots=True)
class ProcessArtifacts:
    geotiff: bytes
    user_data: Mapping[str, Any]


def build_process_request(
    web_mercator_geometry: Mapping[str, Any], interval_from: datetime, interval_to: datetime
) -> Mapping[str, Any]:
    if web_mercator_geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("process AOI must be Polygon or MultiPolygon")
    if interval_from.tzinfo is None or interval_to.tzinfo is None or interval_from >= interval_to:
        raise ValueError("process interval must be ordered and timezone-aware")
    return {
        "input": {
            "bounds": {
                "geometry": dict(web_mercator_geometry),
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/3857"},
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": _utc(interval_from),
                        "to": _utc(interval_to),
                    },
                    "mosaickingOrder": "leastCC",
                    "maxCloudCoverage": 100,
                },
            }],
        },
        "output": {
            "resx": 10,
            "resy": 10,
            "responses": [
                {"identifier": "default", "format": {"type": "image/tiff"}},
                {"identifier": "userdata", "format": {"type": "application/json"}},
            ],
        },
        "evalscript": PROCESS_EVALSCRIPT,
    }


def parse_process_response(body: bytes, content_type: str) -> ProcessArtifacts:
    if "multipart" not in content_type:
        raise ValueError("Process API response is not multipart")
    message = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    )
    geotiff: bytes | None = None
    user_data: Mapping[str, Any] | None = None
    for part in message.iter_parts():
        payload = part.get_payload(decode=True) or b""
        media_type = part.get_content_type()
        if media_type == "image/tiff":
            geotiff = payload
        elif media_type == "application/json":
            decoded = json.loads(payload)
            if isinstance(decoded, Mapping):
                user_data = decoded
    if geotiff is None or not geotiff.startswith((b"II*\x00", b"MM\x00*")):
        raise ValueError("Process API response has no valid GeoTIFF")
    if user_data is None:
        raise ValueError("Process API response has no userdata JSON")
    return ProcessArtifacts(geotiff=geotiff, user_data=user_data)


class SentinelProcessClient:
    def __init__(self, transport: UrllibJsonTransport, tokens: CopernicusTokenProvider) -> None:
        self._transport = transport
        self._tokens = tokens

    def process(self, request: Mapping[str, Any]) -> ProcessArtifacts:
        response = self._transport.post_bytes(
            SENTINEL_PROCESS_URL,
            request,
            headers={
                "Authorization": f"Bearer {self._tokens.get_token()}",
                "Accept": "multipart/mixed",
            },
        )
        return parse_process_response(response.body, response.content_type)


def cache_process_artifacts(
    database_url: str,
    scene_id: UUID,
    geometry_hash: str,
    artifacts: ProcessArtifacts,
    root: Path = Path("data/processed/sentinel"),
) -> tuple[Path, Path]:
    directory = root / str(scene_id) / geometry_hash
    directory.mkdir(parents=True, exist_ok=True)
    tif_path = directory / "ndvi.tif"
    metadata_path = directory / "userdata.json"
    tif_path.write_bytes(artifacts.geotiff)
    metadata_bytes = json.dumps(
        artifacts.user_data, ensure_ascii=False, sort_keys=True, indent=2
    ).encode() + b"\n"
    metadata_path.write_bytes(metadata_bytes)
    db = database_url.replace("postgresql+psycopg://", "postgresql://")
    role_suffix = geometry_hash[:16]
    with psycopg.connect(db) as connection, connection.cursor() as cursor:
        for role, path, content, media_type in (
            (f"ndvi_aoi_crop_{role_suffix}", tif_path, artifacts.geotiff, "image/tiff"),
            (f"process_userdata_{role_suffix}", metadata_path, metadata_bytes, "application/json"),
        ):
            cursor.execute(
                """
                INSERT INTO satellite_asset (
                    satellite_scene_id, asset_role, storage_uri, checksum_sha256, media_type
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (satellite_scene_id, asset_role, checksum_sha256) DO NOTHING
                """,
                (scene_id, role, path.as_posix(), hashlib.sha256(content).hexdigest(), media_type),
            )
        cursor.execute(
            """
            UPDATE satellite_scene
            SET cache_status = 'partially_cached', cached_at = COALESCE(cached_at, now())
            WHERE id = %s AND cache_status IN ('discovered', 'partially_cached')
            """,
            (scene_id,),
        )
    return tif_path, metadata_path


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
