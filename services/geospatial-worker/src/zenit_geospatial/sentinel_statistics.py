"""Quality-gated Sentinel-2 NDVI statistics for prepared 100 m AOIs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from zenit_geospatial.satellite_http import CopernicusTokenProvider, JsonTransport

SENTINEL_STATISTICS_URL = "https://sh.dataspace.copernicus.eu/statistics/v1"
PROCESSING_VERSION = "sentinel-ndvi-scl-v1"

NDVI_SCL_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}

function isValid(sample) {
  const invalidScl = [0, 1, 3, 6, 7, 8, 9, 10, 11];
  return sample.dataMask === 1 && !invalidScl.includes(sample.SCL);
}

function evaluatePixel(sample) {
  if (!isValid(sample)) return { ndvi: [0], dataMask: [0] };
  const denominator = sample.B08 + sample.B04;
  if (denominator === 0) return { ndvi: [0], dataMask: [0] };
  return {
    ndvi: [(sample.B08 - sample.B04) / denominator],
    dataMask: [1]
  };
}
"""


class StatisticalResponseError(ValueError):
    """Raised when a Statistical API response cannot be normalized."""


class QualityStatus(StrEnum):
    ACCEPTED = "accepted"
    WARNING = "quality_warning"
    REJECTED = "rejected"
    NO_OBSERVATION = "no_observation"


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    accepted_valid_ratio: float = 0.70
    warning_valid_ratio: float = 0.40

    def __post_init__(self) -> None:
        if not 0 <= self.warning_valid_ratio <= self.accepted_valid_ratio <= 1:
            raise ValueError("quality thresholds must satisfy 0 <= warning <= accepted <= 1")

    def classify(self, valid_pixel_ratio: float | None) -> QualityStatus:
        if valid_pixel_ratio is None:
            return QualityStatus.NO_OBSERVATION
        if valid_pixel_ratio >= self.accepted_valid_ratio:
            return QualityStatus.ACCEPTED
        if valid_pixel_ratio >= self.warning_valid_ratio:
            return QualityStatus.WARNING
        return QualityStatus.REJECTED


@dataclass(frozen=True, slots=True)
class SentinelStatistic:
    interval_from: datetime
    interval_to: datetime
    mean_ndvi: float | None
    ndvi_std: float | None
    ndvi_p25: float | None
    ndvi_p50: float | None
    ndvi_p75: float | None
    sample_count: int
    no_data_count: int
    valid_pixel_ratio: float | None
    quality_status: QualityStatus


def build_statistical_request(
    geometry: Mapping[str, Any],
    interval_from: datetime,
    interval_to: datetime,
    *,
    max_cloud_coverage: float = 100.0,
) -> Mapping[str, Any]:
    if interval_from.tzinfo is None or interval_to.tzinfo is None:
        raise ValueError("statistical interval must be timezone-aware")
    if interval_from >= interval_to:
        raise ValueError("statistical interval start must be before end")
    if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("statistical AOI must be Polygon or MultiPolygon")
    if not 0 <= max_cloud_coverage <= 100:
        raise ValueError("max cloud coverage must be between 0 and 100")
    return {
        "input": {
            "bounds": {
                "geometry": dict(geometry),
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "maxCloudCoverage": max_cloud_coverage,
                        "mosaickingOrder": "leastCC",
                    },
                }
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": _format_utc(interval_from),
                "to": _format_utc(interval_to),
            },
            "aggregationInterval": {"of": "P1D"},
            "resx": 10,
            "resy": 10,
            "evalscript": NDVI_SCL_EVALSCRIPT,
        },
        "calculations": {
            "ndvi": {
                "statistics": {
                    "default": {"percentiles": {"k": [25, 50, 75]}}
                }
            }
        },
    }


def parse_statistical_response(
    payload: Mapping[str, Any], policy: QualityPolicy | None = None
) -> tuple[SentinelStatistic, ...]:
    active_policy = policy or QualityPolicy()
    data = payload.get("data")
    if not isinstance(data, list):
        raise StatisticalResponseError("Statistical API response is missing data")
    return tuple(_parse_interval(item, active_policy) for item in data)


def _parse_interval(item: Any, policy: QualityPolicy) -> SentinelStatistic:
    if not isinstance(item, Mapping):
        raise StatisticalResponseError("Statistical API interval must be an object")
    interval = item.get("interval")
    if not isinstance(interval, Mapping):
        raise StatisticalResponseError("Statistical API interval metadata is missing")
    interval_from = _parse_datetime(interval.get("from"))
    interval_to = _parse_datetime(interval.get("to"))
    stats = _extract_stats(item)
    sample_count = _integer(stats.get("sampleCount"), "sampleCount")
    no_data_count = _integer(stats.get("noDataCount"), "noDataCount")
    if no_data_count > sample_count:
        raise StatisticalResponseError("noDataCount cannot exceed sampleCount")
    valid_pixel_ratio = (
        (sample_count - no_data_count) / sample_count if sample_count > 0 else None
    )
    percentiles = stats.get("percentiles", {})
    if not isinstance(percentiles, Mapping):
        raise StatisticalResponseError("Statistical API percentiles must be an object")
    return SentinelStatistic(
        interval_from=interval_from,
        interval_to=interval_to,
        mean_ndvi=_optional_float(stats.get("mean")),
        ndvi_std=_optional_float(stats.get("stDev")),
        ndvi_p25=_percentile(percentiles, 25),
        ndvi_p50=_percentile(percentiles, 50),
        ndvi_p75=_percentile(percentiles, 75),
        sample_count=sample_count,
        no_data_count=no_data_count,
        valid_pixel_ratio=valid_pixel_ratio,
        quality_status=policy.classify(valid_pixel_ratio),
    )


def _extract_stats(item: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        stats = item["outputs"]["ndvi"]["bands"]["B0"]["stats"]
    except (KeyError, TypeError) as error:
        raise StatisticalResponseError("Statistical API NDVI stats are missing") from error
    if not isinstance(stats, Mapping):
        raise StatisticalResponseError("Statistical API NDVI stats must be an object")
    return stats


def _parse_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise StatisticalResponseError("Statistical API interval datetime is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise StatisticalResponseError("Statistical API interval datetime is invalid") from error
    if parsed.tzinfo is None:
        raise StatisticalResponseError("Statistical API interval datetime lacks timezone")
    return parsed.astimezone(UTC)


def _integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise StatisticalResponseError(f"Statistical API {field} is invalid")
    return value


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise StatisticalResponseError("Statistical API numeric statistic is invalid")
    return float(value)


def _percentile(values: Mapping[str, Any], percentile: int) -> float | None:
    for key in (str(percentile), f"{percentile}.0"):
        if key in values:
            return _optional_float(values[key])
    return None


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class SentinelStatisticalClient:
    def __init__(self, transport: JsonTransport, token_provider: CopernicusTokenProvider) -> None:
        self._transport = transport
        self._token_provider = token_provider

    def analyze(
        self, payload: Mapping[str, Any], policy: QualityPolicy | None = None
    ) -> tuple[SentinelStatistic, ...]:
        response = self._transport.post_json(
            SENTINEL_STATISTICS_URL,
            payload,
            headers={
                "Authorization": f"Bearer {self._token_provider.get_token()}",
                "Accept": "application/json",
            },
        )
        return parse_statistical_response(response, policy)
