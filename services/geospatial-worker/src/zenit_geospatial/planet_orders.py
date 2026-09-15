"""Bounded Planet Orders API access for one reviewed academic test order."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

from zenit_geospatial.satellite_http import BinaryResponse, SatelliteAuthenticationError

PLANET_ORDERS_URL = "https://api.planet.com/compute/ops/orders/v2"
PLANET_ITEM_TYPE = "PSScene"
PLANET_PRODUCT_BUNDLE = "analytic_udm2"
PLANET_ORDER_STATES = frozenset({"queued", "running", "success", "failed", "cancelled"})
EXPECTED_ANALYTIC_UDM2_ASSETS = frozenset(
    {"ortho_analytic_4b", "ortho_analytic_4b_xml", "ortho_udm2"}
)


class PlanetOrderTransport(Protocol):
    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]: ...

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]: ...

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        maximum_bytes: int | None = None,
    ) -> BinaryResponse: ...


class PlanetOrderError(RuntimeError):
    """Raised when an Order response violates the bounded acquisition contract."""


@dataclass(frozen=True, slots=True)
class OrderResult:
    name: str
    location: str
    asset_role: str


def build_scenes_order_request(
    *,
    name: str,
    scene_id: str,
    aoi: Mapping[str, Any],
    product_bundle: str = PLANET_PRODUCT_BUNDLE,
) -> dict[str, Any]:
    if not name.strip():
        raise ValueError("order name must not be empty")
    if not scene_id.strip():
        raise ValueError("scene_id must not be empty")
    if product_bundle != PLANET_PRODUCT_BUNDLE:
        raise ValueError("PLANET-004 is restricted to analytic_udm2")
    _validate_aoi(aoi)
    return {
        "name": name,
        "source_type": "scenes",
        "products": [
            {
                "item_ids": [scene_id],
                "item_type": PLANET_ITEM_TYPE,
                "product_bundle": product_bundle,
            }
        ],
        "tools": [{"clip": {"aoi": dict(aoi)}}],
    }


class PlanetOrdersClient:
    """Backend-only Orders API client; signed download URLs never leave this process."""

    def __init__(self, transport: PlanetOrderTransport, api_key: str) -> None:
        if not api_key:
            raise SatelliteAuthenticationError("Planet API key is not configured")
        self._transport = transport
        self._api_key = api_key

    def create(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        response = self._transport.post_json(
            PLANET_ORDERS_URL,
            payload,
            headers={"Authorization": f"api-key {self._api_key}"},
        )
        order_id = response.get("id")
        if not isinstance(order_id, str) or not order_id:
            raise PlanetOrderError("Planet Order response has no id")
        return response

    def get(self, order_id: str) -> Mapping[str, Any]:
        _validate_order_id(order_id)
        return self._transport.get_json(
            f"{PLANET_ORDERS_URL}/{order_id}",
            headers={"Authorization": f"api-key {self._api_key}"},
        )

    def download(self, location: str, *, maximum_bytes: int) -> BinaryResponse:
        _validate_download_location(location)
        return self._transport.get_bytes(location, maximum_bytes=maximum_bytes)


def order_id(response: Mapping[str, Any]) -> str:
    value = response.get("id")
    if not isinstance(value, str) or not value:
        raise PlanetOrderError("Planet Order response has no id")
    _validate_order_id(value)
    return value


def order_state(response: Mapping[str, Any]) -> str:
    value = response.get("state")
    if not isinstance(value, str) or value not in PLANET_ORDER_STATES:
        raise PlanetOrderError("Planet Order response has an unsupported state")
    return value


def order_results(response: Mapping[str, Any]) -> tuple[OrderResult, ...]:
    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        raise PlanetOrderError("Planet Order response has no results array")
    results: list[OrderResult] = []
    for result in raw_results:
        if not isinstance(result, Mapping):
            raise PlanetOrderError("Planet Order response has an invalid result")
        delivery = result.get("delivery")
        if delivery != "success":
            continue
        name = result.get("name")
        location = result.get("location")
        if not isinstance(name, str) or not name:
            raise PlanetOrderError("Planet Order result has no name")
        if not isinstance(location, str) or not location:
            raise PlanetOrderError("Planet Order result has no download location")
        _validate_download_location(location)
        results.append(OrderResult(name=name, location=location, asset_role=asset_role(name)))
    return tuple(results)


def asset_role(name: str) -> str:
    """Map Planet's result path to the stable role used in satellite_asset."""

    normalized = name.casefold()
    if "ortho_analytic_4b_xml" in normalized:
        return "ortho_analytic_4b_xml"
    if "ortho_analytic_4b" in normalized:
        return "ortho_analytic_4b"
    if "ortho_udm2" in normalized:
        return "ortho_udm2"
    return "planet_order_result"


def media_type(content_type: str, name: str) -> str:
    value = content_type.split(";", 1)[0].strip().lower()
    if value and value != "application/octet-stream":
        return value
    suffix = name.casefold().rsplit(".", 1)[-1] if "." in name else ""
    return {
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "xml": "application/xml",
        "json": "application/json",
        "zip": "application/zip",
    }.get(suffix, "application/octet-stream")


def _validate_aoi(aoi: Mapping[str, Any]) -> None:
    if aoi.get("type") != "Polygon":
        raise ValueError("Order AOI must be a GeoJSON Polygon")
    coordinates = aoi.get("coordinates")
    if not isinstance(coordinates, Sequence) or not coordinates:
        raise ValueError("Order AOI Polygon must contain coordinates")
    ring = coordinates[0]
    if not isinstance(ring, Sequence) or len(ring) < 4:
        raise ValueError("Order AOI Polygon ring is too short")
    if ring[0] != ring[-1]:
        raise ValueError("Order AOI Polygon ring must be closed")


def _validate_order_id(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,200}", value):
        raise ValueError("invalid Planet Order id")


def _validate_download_location(value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.planet.com"
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.startswith("/compute/ops/download/")
    ):
        raise PlanetOrderError("Planet Order result has an invalid download location")
