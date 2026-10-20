"""PLANET-008: offline NDVI statistics per zone from cached PlanetScope assets.

Everything here works on bytes already stored and verified locally: no provider
call, no download and no quota use. The result is spectral evidence per zone and
is always inconclusive; it never becomes height, a historical class or an
authorization.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np
from rasterio.io import MemoryFile
from rasterio.mask import mask as rasterio_mask
from rasterio.warp import transform_geom

from zenit_geospatial.sentinel_statistics import QualityPolicy, QualityStatus

PROCESSOR_VERSION = "zenit-planet-offline-ndvi-v1"
RULE_VERSION = "planet-offline-quality-2026-09-15.1"

# PSScene analytic_udm2 surface reflectance band order and the UDM2 clear mask.
RED_BAND = 3
NIR_BAND = 4
UDM2_CLEAR_BAND = 1


class ProcessingError(RuntimeError):
    """Raised when cached bytes cannot produce a defensible zone statistic."""


@dataclass(frozen=True, slots=True)
class ZoneStatistics:
    segment_zone_id: UUID
    total_pixels: int
    valid_pixels: int
    mean_ndvi: float | None
    min_ndvi: float | None
    max_ndvi: float | None
    std_ndvi: float | None
    quality_status: str

    @property
    def valid_pixel_percent(self) -> float:
        if self.total_pixels == 0:
            return 0.0
        return round(self.valid_pixels / self.total_pixels * 100, 2)


def _clip(dataset, geometry: Mapping[str, Any], geometry_srid: int) -> np.ndarray:
    target = dataset.crs
    source = f"EPSG:{geometry_srid}"
    shape = transform_geom(source, target, dict(geometry)) if target else dict(geometry)
    try:
        clipped, _ = rasterio_mask(dataset, [shape], crop=True, filled=True, nodata=0)
    except ValueError as error:  # geometry outside the raster extent
        raise ProcessingError(
            f"zone geometry does not overlap the cached raster: {error}"
        ) from None
    return clipped


def zone_statistics(
    *,
    segment_zone_id: UUID,
    analytic: bytes,
    udm2: bytes,
    geometry: Mapping[str, Any],
    geometry_srid: int = 31983,
    policy: QualityPolicy | None = None,
) -> ZoneStatistics:
    """Mask clouds, shadow and invalid pixels with UDM2 before any NDVI statistic."""
    active = policy or QualityPolicy()
    with (
        MemoryFile(analytic) as analytic_file,
        MemoryFile(udm2) as udm2_file,
        analytic_file.open() as analytic_dataset,
        udm2_file.open() as udm2_dataset,
    ):
        if analytic_dataset.count < NIR_BAND:
            raise ProcessingError("cached analytic asset does not carry a NIR band")
        if udm2_dataset.count < UDM2_CLEAR_BAND:
            raise ProcessingError("cached UDM2 asset does not carry the clear band")
        if (analytic_dataset.width, analytic_dataset.height) != (
            udm2_dataset.width,
            udm2_dataset.height,
        ):
            raise ProcessingError("analytic and UDM2 assets do not share the same grid")
        analytic_pixels = _clip(analytic_dataset, geometry, geometry_srid).astype("float64")
        udm2_pixels = _clip(udm2_dataset, geometry, geometry_srid)

    red = analytic_pixels[RED_BAND - 1]
    nir = analytic_pixels[NIR_BAND - 1]
    clear = udm2_pixels[UDM2_CLEAR_BAND - 1] == 1
    denominator = nir + red
    usable = clear & (denominator != 0)
    total_pixels = int(red.size)
    valid_pixels = int(np.count_nonzero(usable))
    if valid_pixels == 0:
        return ZoneStatistics(
            segment_zone_id=segment_zone_id,
            total_pixels=total_pixels,
            valid_pixels=0,
            mean_ndvi=None,
            min_ndvi=None,
            max_ndvi=None,
            std_ndvi=None,
            quality_status=QualityStatus.NO_OBSERVATION,
        )
    ndvi = (nir[usable] - red[usable]) / denominator[usable]
    ratio = valid_pixels / total_pixels if total_pixels else None
    return ZoneStatistics(
        segment_zone_id=segment_zone_id,
        total_pixels=total_pixels,
        valid_pixels=valid_pixels,
        mean_ndvi=round(float(np.mean(ndvi)), 6),
        min_ndvi=round(float(np.min(ndvi)), 6),
        max_ndvi=round(float(np.max(ndvi)), 6),
        std_ndvi=round(float(np.std(ndvi)), 6),
        quality_status=active.classify(ratio),
    )


def idempotency_key(
    *,
    scene_id: UUID,
    segment_zone_id: UUID,
    analytic_checksum: str,
    udm2_checksum: str,
    geometry_hash: str,
) -> str:
    canonical = {
        "analytic_checksum": analytic_checksum,
        "geometry_hash": geometry_hash,
        "processor_version": PROCESSOR_VERSION,
        "rule_version": RULE_VERSION,
        "scene_id": str(scene_id),
        "segment_zone_id": str(segment_zone_id),
        "udm2_checksum": udm2_checksum,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def geometry_hash(geometry: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(geometry), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def explanation(
    statistics: ZoneStatistics,
    *,
    analytic_checksum: str,
    udm2_checksum: str,
    geometry_hash_value: str,
    zone_data_status: str,
) -> dict[str, Any]:
    return {
        "processor_version": PROCESSOR_VERSION,
        "rule_version": RULE_VERSION,
        "source": "cached_planet_analytic_udm2",
        "offline": True,
        "analytic_checksum_sha256": analytic_checksum,
        "udm2_checksum_sha256": udm2_checksum,
        "geometry_hash": geometry_hash_value,
        "zone_data_status": zone_data_status,
        "quality_status": statistics.quality_status,
        "valid_pixel_percent": statistics.valid_pixel_percent,
        "total_pixels": statistics.total_pixels,
        "valid_pixels": statistics.valid_pixels,
        "ndvi": {
            "mean": statistics.mean_ndvi,
            "min": statistics.min_ndvi,
            "max": statistics.max_ndvi,
            "std": statistics.std_ndvi,
        },
        "result_data_status": "inconclusive",
        "reasons": [
            "NDVI is a spectral response and never a vegetation height in centimetres.",
            "The zone geometry is prepared and derived from an estimated axis.",
            "Cloud, shadow and invalid pixels were masked with UDM2 before the statistic.",
            "Field ground truth is required before any conclusion or intervention.",
        ],
    }


def summarize(statistics: Sequence[ZoneStatistics]) -> dict[str, Any]:
    by_quality: dict[str, int] = {}
    for item in statistics:
        by_quality[item.quality_status] = by_quality.get(item.quality_status, 0) + 1
    return {
        "processor_version": PROCESSOR_VERSION,
        "rule_version": RULE_VERSION,
        "zones": len(statistics),
        "zones_by_quality": dict(sorted(by_quality.items())),
        "provider_calls": 0,
        "conclusion": "inconclusive",
        "eligible_for_operations": False,
        "eligible_for_official_reporting": False,
    }
