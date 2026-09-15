"""Create exactly one bounded Planet Order and cache its approved assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from typing import Any

from zenit_api.config import Settings
from zenit_geospatial.planet_order_repository import PostgresPlanetOrderRepository
from zenit_geospatial.planet_orders import (
    EXPECTED_ANALYTIC_UDM2_ASSETS,
    PlanetOrderError,
    PlanetOrdersClient,
    build_scenes_order_request,
    media_type,
    order_id,
    order_results,
    order_state,
)
from zenit_geospatial.satellite_catalog import PostgresSatelliteCatalog
from zenit_geospatial.satellite_http import PlanetCatalogClient, UrllibJsonTransport
from zenit_geospatial.satellite_providers import BoundingBox, PlanetDataProvider, SearchWindow
from zenit_geospatial.satellite_storage import EncryptedSatelliteStore

MAX_AREA_M2 = 10_000.0
MAX_BYTES = 104_857_600
DEFAULT_BUFFER_M = 25.0
DEFAULT_RETENTION_DAYS = 30
DEFAULT_POLL_SECONDS = 5.0
DEFAULT_WAIT_SECONDS = 300.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create one bounded Planet analytic_udm2 Order and cache its assets"
    )
    parser.add_argument("--road-code", default="SP021")
    parser.add_argument("--segment-index", type=int, default=195)
    parser.add_argument("--from-date", type=date.fromisoformat, default=date(2026, 8, 1))
    parser.add_argument("--to-date", type=date.fromisoformat, default=date(2026, 8, 7))
    parser.add_argument("--buffer-m", type=float, default=DEFAULT_BUFFER_M)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--max-area-m2", type=float, default=MAX_AREA_M2)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--wait-seconds", type=float, default=DEFAULT_WAIT_SECONDS)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="confirm the single external Order and bounded download",
    )
    return parser


def run(
    arguments: argparse.Namespace,
    settings: Settings | None = None,
    *,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, object]:
    if not arguments.execute:
        raise RuntimeError("Planet Order/download requires the --execute confirmation")
    active = settings or Settings()
    if active.planet_api_key is None:
        raise RuntimeError("Planet API key is not configured")
    _validate_limits(arguments)
    start = datetime.combine(arguments.from_date, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(arguments.to_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    if start >= end:
        raise ValueError("from-date must not be after to-date")

    database_url = _local_database_url(active.database_url)
    repository = PostgresPlanetOrderRepository(database_url)
    aoi = repository.prepared_segment_aoi(
        road_code=arguments.road_code,
        segment_index=arguments.segment_index,
        buffer_m=arguments.buffer_m,
    )
    if aoi.data_status != "estimated" or aoi.eligible_for_operations:
        raise PlanetOrderError("Order AOI must remain estimated and non-operational")
    if aoi.area_m2 > arguments.max_area_m2:
        raise PlanetOrderError("Order AOI exceeds the approved area limit")
    bbox = BoundingBox(*_bbox(aoi.geometry))
    provider = PlanetDataProvider()
    search_payload = provider.build_search_request(
        bbox,
        SearchWindow(start, end),
        limit=arguments.limit,
        require_download_permission=True,
    )
    catalog_page = PlanetCatalogClient(
        UrllibJsonTransport(timeout_seconds=30),
        active.planet_api_key.get_secret_value(),
        provider,
    ).search(search_payload)
    if catalog_page.next_url is not None:
        raise PlanetOrderError("catalog result exceeded the bounded first page")
    if not catalog_page.acquisitions:
        raise LookupError("no downloadable Planet scene intersects the prepared AOI")
    selected = min(
        catalog_page.acquisitions,
        key=lambda item: (
            item.cloud_cover_percent if item.cloud_cover_percent is not None else 100.0,
            -item.acquired_at.timestamp(),
        ),
    )

    discovered_at = datetime.now(UTC)
    scene = PostgresSatelliteCatalog(database_url).register(selected, discovered_at)
    order_name = f"zenit-planet-004-{arguments.road_code}-{arguments.segment_index}"
    request = build_scenes_order_request(
        name=order_name,
        scene_id=selected.external_scene_id,
        aoi=aoi.geometry,
    )
    request_checksum = _checksum(request)
    existing = repository.find_by_request_checksum(request_checksum)
    order_client = PlanetOrdersClient(
        UrllibJsonTransport(timeout_seconds=30),
        active.planet_api_key.get_secret_value(),
    )
    order_created = False
    if existing is None:
        created = order_client.create(request)
        remote_order_id = order_id(created)
        initial_state = _safe_state(created, default="queued")
        lineage_id = repository.create_order(
            external_order_id=remote_order_id,
            order_name=order_name,
            item_ids=[selected.external_scene_id],
            aoi=aoi.geometry,
            aoi_area_m2=aoi.area_m2,
            max_bytes=arguments.max_bytes,
            license_scope="academic-only",
            retention_days=arguments.retention_days,
            destination_bucket=active.object_storage_bucket_raw,
            destination_prefix=f"planet/orders/{remote_order_id}",
            request_checksum=request_checksum,
            response_metadata=_safe_response_metadata(created),
            order_state=initial_state,
        )
        repository.record_event(
            order_id=lineage_id,
            event_type="created",
            order_state=initial_state,
            details={"item_count": 1, "product_bundle": "analytic_udm2"},
        )
        order_created = True
    else:
        lineage_id = existing.id
        remote_order_id = existing.external_order_id
        if existing.order_state in {"failed", "cancelled"}:
            raise PlanetOrderError("the single approved Planet Order is not recoverable")

    snapshot, final_state = _wait_for_order(
        order_client,
        remote_order_id,
        lineage_id,
        repository,
        max_wait_seconds=arguments.wait_seconds,
        poll_seconds=arguments.poll_seconds,
        sleep=sleep,
        monotonic=monotonic,
    )
    if final_state != "success":
        raise PlanetOrderError(f"Planet Order finished in {final_state} state")
    results = order_results(snapshot)
    by_role: dict[str, Any] = {}
    for result in results:
        if result.asset_role in EXPECTED_ANALYTIC_UDM2_ASSETS:
            if result.asset_role in by_role:
                raise PlanetOrderError("Planet Order returned duplicate bundle assets")
            by_role[result.asset_role] = result
    missing = EXPECTED_ANALYTIC_UDM2_ASSETS.difference(by_role)
    if missing:
        raise PlanetOrderError("Planet Order did not return the complete analytic_udm2 bundle")

    storage_settings = active.model_copy(
        update={
            "object_storage_endpoint": _local_object_storage_endpoint(
                active.object_storage_endpoint
            )
        }
    )
    store = EncryptedSatelliteStore(storage_settings)
    downloaded_bytes = 0
    for role in sorted(EXPECTED_ANALYTIC_UDM2_ASSETS):
        result = by_role[role]
        remaining = arguments.max_bytes - downloaded_bytes
        binary = order_client.download(result.location, maximum_bytes=remaining)
        downloaded_bytes += len(binary.body)
        if downloaded_bytes > arguments.max_bytes:
            raise PlanetOrderError("download exceeded the approved byte limit")
        checksum = hashlib.sha256(binary.body).hexdigest()
        stored = store.put_verified(
            order_id=remote_order_id,
            scene_id=selected.external_scene_id,
            asset_role=role,
            content=binary.body,
            media_type=media_type(binary.content_type, result.name),
            checksum_sha256=checksum,
        )
        repository.register_asset(
            order_id=lineage_id,
            scene_id=scene.id,
            asset_role=role,
            storage_uri=stored.storage_uri,
            checksum_sha256=checksum,
            media_type=media_type(binary.content_type, result.name),
        )
        repository.record_event(
            order_id=lineage_id,
            event_type="asset_downloaded",
            order_state="success",
            details={
                "asset_role": role,
                "byte_size": len(binary.body),
                "checksum_sha256": checksum,
            },
        )

    completed_at = datetime.now(UTC)
    repository.mark_scene_cached(scene_id=scene.id, cached_at=completed_at)
    response_metadata = {
        **_safe_response_metadata(snapshot),
        "downloaded_asset_count": len(by_role),
        "downloaded_bytes": downloaded_bytes,
    }
    repository.update_state(
        order_id=lineage_id,
        order_state="success",
        response_metadata=response_metadata,
        downloaded_bytes=downloaded_bytes,
        completed_at=completed_at,
    )
    repository.record_event(
        order_id=lineage_id,
        event_type="status",
        order_state="success",
        details={"downloaded_asset_count": len(by_role), "downloaded_bytes": downloaded_bytes},
    )
    return {
        "catalog_acquisitions": len(catalog_page.acquisitions),
        "selected_scene_id": selected.external_scene_id,
        "scene_cloud_cover_percent": selected.cloud_cover_percent,
        "order_id": remote_order_id,
        "order_created": order_created,
        "order_state": "success",
        "downloaded_assets": len(by_role),
        "downloaded_bytes": downloaded_bytes,
        "aoi_area_m2": round(aoi.area_m2, 2),
        "data_status": "real",
        "eligible_for_operations": False,
        "eligible_for_official_reporting": False,
    }


def _wait_for_order(
    client: PlanetOrdersClient,
    remote_order_id: str,
    lineage_id: Any,
    repository: PostgresPlanetOrderRepository,
    *,
    max_wait_seconds: float,
    poll_seconds: float,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
) -> tuple[Mapping[str, Any], str]:
    deadline = monotonic() + max_wait_seconds
    previous_state: str | None = None
    snapshot: Mapping[str, Any] = {}
    while True:
        snapshot = client.get(remote_order_id)
        state = order_state(snapshot)
        if state != previous_state:
            repository.update_state(
                order_id=lineage_id,
                order_state=state,
                response_metadata=_safe_response_metadata(snapshot),
                downloaded_bytes=0,
                completed_at=None,
            )
            repository.record_event(
                order_id=lineage_id,
                event_type="status",
                order_state=state,
                details={"result_count": _result_count(snapshot)},
            )
            previous_state = state
        if state in {"success", "failed", "cancelled"}:
            return snapshot, state
        if monotonic() >= deadline:
            raise TimeoutError("Planet Order polling exceeded the approved wait limit")
        sleep(min(poll_seconds, max(0.0, deadline - monotonic())))


def _validate_limits(arguments: argparse.Namespace) -> None:
    if not 1 <= arguments.limit <= 25:
        raise ValueError("limit must be between 1 and 25")
    if not 0 < arguments.max_area_m2 <= MAX_AREA_M2:
        raise ValueError("max-area-m2 must be between 0 and 10000")
    if not 0 < arguments.max_bytes <= MAX_BYTES:
        raise ValueError("max-bytes must be between 0 and 104857600")
    if not 1 <= arguments.retention_days <= 365:
        raise ValueError("retention-days must be between 1 and 365")
    if arguments.poll_seconds <= 0 or arguments.wait_seconds <= 0:
        raise ValueError("poll and wait limits must be positive")


def _bbox(geometry: Mapping[str, Any]) -> tuple[float, float, float, float]:
    coordinates = geometry.get("coordinates")
    points = coordinates[0] if isinstance(coordinates, list) and coordinates else []
    if not isinstance(points, list) or len(points) < 4:
        raise ValueError("AOI Polygon has no usable ring")
    values = [(float(point[0]), float(point[1])) for point in points]
    return (
        min(point[0] for point in values),
        min(point[1] for point in values),
        max(point[0] for point in values),
        max(point[1] for point in values),
    )


def _checksum(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_state(response: Mapping[str, Any], *, default: str) -> str:
    value = response.get("state")
    valid_states = {"queued", "running", "success", "failed", "cancelled"}
    return value if isinstance(value, str) and value in valid_states else default


def _result_count(response: Mapping[str, Any]) -> int:
    results = response.get("results")
    return len(results) if isinstance(results, list) else 0


def _safe_response_metadata(response: Mapping[str, Any]) -> dict[str, object]:
    return {
        "state": _safe_state(response, default="queued"),
        "result_count": _result_count(response),
        "has_error_hints": bool(response.get("error_hints")),
        "has_last_message": bool(response.get("last_message")),
    }


def _local_database_url(database_url: str) -> str:
    return database_url.replace("@postgres:", "@localhost:").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def _local_object_storage_endpoint(endpoint: str) -> str:
    return endpoint.replace("http://minio:9000", "http://localhost:9000", 1)


def main() -> None:
    result = run(build_parser().parse_args())
    print(" ".join(f"{key}={str(value).lower()}" for key, value in result.items()))


if __name__ == "__main__":
    main()
