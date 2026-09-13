"""Provider-neutral satellite acquisition discovery for the Sprint 3 pipeline."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from urllib.parse import parse_qsl, urlparse

SENTINEL_CATALOG_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/search"
CBERS_STAC_URL = "https://data.inpe.br/bdc/stac/v1/search"
PLANET_DATA_SEARCH_URL = "https://api.planet.com/data/v1/quick-search"
SENTINEL_COLLECTION = "sentinel-2-l2a"
CBERS_WPM_COLLECTION = "CB4A-WPM-L4-DN-1"
CBERS_WFI_COLLECTION = "CB4A-WFI-L4-SR-1"
PLANET_PS_SCENE_COLLECTION = "PSScene"

ProviderName = Literal["copernicus_sentinel_hub", "inpe_bdc", "planet"]
SensorName = Literal["sentinel-2", "cbers-4a", "planet-scope"]


class ProviderResponseError(ValueError):
    """Raised when a provider response cannot be normalized safely."""


@dataclass(frozen=True, slots=True)
class BoundingBox:
    min_longitude: float
    min_latitude: float
    max_longitude: float
    max_latitude: float

    def __post_init__(self) -> None:
        if not (-180 <= self.min_longitude < self.max_longitude <= 180):
            raise ValueError("longitude bounds must be ordered within [-180, 180]")
        if not (-90 <= self.min_latitude < self.max_latitude <= 90):
            raise ValueError("latitude bounds must be ordered within [-90, 90]")

    def as_list(self) -> list[float]:
        return [
            self.min_longitude,
            self.min_latitude,
            self.max_longitude,
            self.max_latitude,
        ]


@dataclass(frozen=True, slots=True)
class SearchWindow:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("search window datetimes must be timezone-aware")
        if self.start >= self.end:
            raise ValueError("search window start must be before end")

    def as_stac_interval(self) -> str:
        return f"{_format_utc(self.start)}/{_format_utc(self.end)}"


@dataclass(frozen=True, slots=True)
class Acquisition:
    provider: ProviderName
    collection: str
    sensor: SensorName
    external_scene_id: str
    acquired_at: datetime
    bbox: tuple[float, float, float, float] | None
    geometry: Mapping[str, Any] | None
    cloud_cover_percent: float | None
    assets: Mapping[str, str]
    source_metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SearchPage:
    acquisitions: tuple[Acquisition, ...]
    next_url: str | None
    next_token: str | int | None = None


class SatelliteProvider(Protocol):
    """Provider boundary used by discovery orchestration."""

    @property
    def provider_name(self) -> ProviderName: ...

    def build_search_request(
        self, bbox: BoundingBox, window: SearchWindow, *, limit: int = 100
    ) -> Mapping[str, Any]: ...

    def parse_search_page(self, payload: Mapping[str, Any]) -> SearchPage: ...


class SentinelCatalogProvider:
    provider_name: ProviderName = "copernicus_sentinel_hub"

    def build_search_request(
        self, bbox: BoundingBox, window: SearchWindow, *, limit: int = 100
    ) -> Mapping[str, Any]:
        _validate_limit(limit)
        return {
            "bbox": bbox.as_list(),
            "datetime": window.as_stac_interval(),
            "collections": [SENTINEL_COLLECTION],
            "limit": limit,
        }

    def parse_search_page(self, payload: Mapping[str, Any]) -> SearchPage:
        features = _features(payload)
        acquisitions = tuple(
            _parse_feature(
                feature,
                provider=self.provider_name,
                default_collection=SENTINEL_COLLECTION,
                sensor="sentinel-2",
                include_assets=False,
            )
            for feature in features
        )
        return SearchPage(
            acquisitions=acquisitions,
            next_url=_next_link(payload),
            next_token=_sentinel_next_token(payload),
        )


class CbersStacProvider:
    provider_name: ProviderName = "inpe_bdc"

    def __init__(self, collection: str = CBERS_WPM_COLLECTION) -> None:
        if collection not in {CBERS_WPM_COLLECTION, CBERS_WFI_COLLECTION}:
            raise ValueError("unsupported CBERS collection")
        self.collection = collection

    def build_search_request(
        self, bbox: BoundingBox, window: SearchWindow, *, limit: int = 100
    ) -> Mapping[str, Any]:
        _validate_limit(limit, maximum=10_000)
        return {
            "collections": [self.collection],
            "bbox": bbox.as_list(),
            "datetime": window.as_stac_interval(),
            "limit": limit,
        }

    def parse_search_page(self, payload: Mapping[str, Any]) -> SearchPage:
        features = _features(payload)
        acquisitions = tuple(
            _parse_feature(
                feature,
                provider=self.provider_name,
                default_collection=self.collection,
                sensor="cbers-4a",
                include_assets=True,
            )
            for feature in features
        )
        return SearchPage(acquisitions=acquisitions, next_url=_next_link(payload))


class PlanetDataProvider:
    """Normalize Planet Data API PSScene discovery without consuming download quota."""

    provider_name: ProviderName = "planet"

    def build_search_request(
        self, bbox: BoundingBox, window: SearchWindow, *, limit: int = 100
    ) -> Mapping[str, Any]:
        _validate_limit(limit, maximum=250)
        min_lon, min_lat, max_lon, max_lat = bbox.as_list()
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat],
                ]
            ],
        }
        return {
            "item_types": [PLANET_PS_SCENE_COLLECTION],
            "filter": {
                "type": "AndFilter",
                "config": [
                    {
                        "type": "GeometryFilter",
                        "field_name": "geometry",
                        "config": geometry,
                    },
                    {
                        "type": "DateRangeFilter",
                        "field_name": "acquired",
                        "config": {
                            "gte": _format_utc(window.start),
                            "lte": _format_utc(window.end),
                        },
                    },
                ],
            },
            "_page_size": limit,
        }

    def parse_search_page(self, payload: Mapping[str, Any]) -> SearchPage:
        acquisitions = tuple(
            _parse_feature(
                feature,
                provider=self.provider_name,
                default_collection=PLANET_PS_SCENE_COLLECTION,
                sensor="planet-scope",
                include_assets=False,
                datetime_property="acquired",
                cloud_cover_multiplier=100.0,
            )
            for feature in _features(payload)
        )
        return SearchPage(acquisitions=acquisitions, next_url=_planet_next_link(payload))


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_limit(limit: int, *, maximum: int = 1_000) -> None:
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")


def _features(payload: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    features = payload.get("features")
    if not isinstance(features, list):
        raise ProviderResponseError("provider response is missing a features array")
    if not all(isinstance(feature, Mapping) for feature in features):
        raise ProviderResponseError("provider response contains a non-object feature")
    return features


def _parse_feature(
    feature: Mapping[str, Any],
    *,
    provider: ProviderName,
    default_collection: str,
    sensor: SensorName,
    include_assets: bool,
    datetime_property: str = "datetime",
    cloud_cover_multiplier: float = 1.0,
) -> Acquisition:
    scene_id = feature.get("id")
    if not isinstance(scene_id, str) or not scene_id:
        raise ProviderResponseError("provider feature is missing its id")
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        raise ProviderResponseError(f"provider feature {scene_id!r} has no properties object")
    acquired_at = _parse_datetime(properties.get(datetime_property), scene_id)
    collection_value = feature.get("collection", feature.get("item_type", default_collection))
    if not isinstance(collection_value, str) or not collection_value:
        raise ProviderResponseError(f"provider feature {scene_id!r} has an invalid collection")

    bbox = _parse_bbox(feature.get("bbox"), scene_id)
    geometry_value = feature.get("geometry")
    geometry = geometry_value if isinstance(geometry_value, Mapping) else None
    cloud_cover_value = properties.get("eo:cloud_cover", properties.get("cloud_cover"))
    cloud_cover = _optional_percentage(cloud_cover_value, scene_id, cloud_cover_multiplier)
    assets = _asset_hrefs(feature.get("assets"), scene_id) if include_assets else {}

    return Acquisition(
        provider=provider,
        collection=collection_value,
        sensor=sensor,
        external_scene_id=scene_id,
        acquired_at=acquired_at,
        bbox=bbox,
        geometry=geometry,
        cloud_cover_percent=cloud_cover,
        assets=assets,
        source_metadata=dict(properties),
    )


def _parse_datetime(value: Any, scene_id: str) -> datetime:
    if not isinstance(value, str):
        raise ProviderResponseError(f"provider feature {scene_id!r} has no acquisition datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProviderResponseError(
            f"provider feature {scene_id!r} has an invalid acquisition datetime"
        ) from error
    if parsed.tzinfo is None:
        raise ProviderResponseError(
            f"provider feature {scene_id!r} acquisition datetime lacks a timezone"
        )
    return parsed.astimezone(UTC)


def _parse_bbox(value: Any, scene_id: str) -> tuple[float, float, float, float] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) < 4:
        raise ProviderResponseError(f"provider feature {scene_id!r} has an invalid bbox")
    try:
        numbers = tuple(float(number) for number in value[:4])
    except (TypeError, ValueError) as error:
        raise ProviderResponseError(f"provider feature {scene_id!r} has an invalid bbox") from error
    return numbers  # type: ignore[return-value]


def _optional_percentage(value: Any, scene_id: str, multiplier: float = 1.0) -> float | None:
    if value is None:
        return None
    try:
        number = float(value) * multiplier
    except (TypeError, ValueError) as error:
        raise ProviderResponseError(
            f"provider feature {scene_id!r} has invalid cloud cover"
        ) from error
    if not 0 <= number <= 100:
        raise ProviderResponseError(f"provider feature {scene_id!r} cloud cover is out of range")
    return number


def _planet_next_link(payload: Mapping[str, Any]) -> str | None:
    links = payload.get("_links")
    if links is None:
        return None
    if not isinstance(links, Mapping):
        raise ProviderResponseError("Planet response _links must be an object")
    next_url = links.get("_next")
    if next_url is None:
        return None
    if not isinstance(next_url, str):
        raise ProviderResponseError("Planet response has an invalid next link")
    parsed = urlparse(next_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.planet.com"
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.startswith("/data/v1/")
    ):
        raise ProviderResponseError("Planet response has an invalid next link")
    if any(key.casefold() == "api_key" for key, _ in parse_qsl(parsed.query)):
        raise ProviderResponseError("Planet response next link contains a credential")
    return next_url


def _asset_hrefs(value: Any, scene_id: str) -> Mapping[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ProviderResponseError(f"provider feature {scene_id!r} has invalid assets")
    hrefs: dict[str, str] = {}
    for role, metadata in value.items():
        if not isinstance(role, str) or not isinstance(metadata, Mapping):
            continue
        href = metadata.get("href")
        if isinstance(href, str) and href:
            hrefs[role] = href
    return hrefs


def _next_link(payload: Mapping[str, Any]) -> str | None:
    links = payload.get("links", [])
    if not isinstance(links, list):
        raise ProviderResponseError("provider response links must be an array")
    for link in links:
        if isinstance(link, Mapping) and link.get("rel") == "next":
            href = link.get("href")
            if not isinstance(href, str) or not href:
                raise ProviderResponseError("provider next link has no href")
            return href
    return None


def _sentinel_next_token(payload: Mapping[str, Any]) -> str | int | None:
    context = payload.get("context")
    if context is None:
        return None
    if not isinstance(context, Mapping):
        raise ProviderResponseError("provider response context must be an object")
    token = context.get("next")
    if token is None:
        return None
    if not isinstance(token, (str, int)) or isinstance(token, bool):
        raise ProviderResponseError("provider next token has an invalid type")
    return token
