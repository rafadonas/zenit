"""Reproducible command-line entry point for the prepared Sentinel pipeline."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta

import psycopg

from zenit_api.config import Settings
from zenit_geospatial.satellite_catalog import PostgresSatelliteCatalog
from zenit_geospatial.satellite_http import (
    CopernicusTokenProvider,
    SentinelCatalogClient,
    UrllibJsonTransport,
)
from zenit_geospatial.satellite_providers import BoundingBox, SearchWindow, SentinelCatalogProvider
from zenit_geospatial.sentinel_process import (
    SentinelProcessClient,
    build_process_request,
    cache_process_artifacts,
)
from zenit_geospatial.sentinel_statistics import (
    SentinelStatisticalClient,
    build_statistical_request,
)
from zenit_geospatial.statistical_persistence import PostgresStatisticalAnalysisRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the idempotent Sentinel pipeline for one prepared, non-operational AOI"
    )
    parser.add_argument("--road-code", default="SP021")
    parser.add_argument("--segment-index", type=int, required=True)
    parser.add_argument("--zone", choices=("left", "right"), required=True)
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--to-date", type=date.fromisoformat, required=True)
    parser.add_argument("--limit", type=int, default=5)
    return parser


def _local_database_url(database_url: str) -> str:
    return database_url.replace("@postgres:", "@localhost:").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def run(arguments: argparse.Namespace, settings: Settings | None = None) -> dict[str, object]:
    active = settings or Settings()
    if not active.copernicus_client_id or not active.copernicus_client_secret:
        raise RuntimeError("Copernicus credentials are not configured")
    start = datetime.combine(arguments.from_date, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(arguments.to_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    if start >= end:
        raise ValueError("from-date must not be after to-date")
    database_url = _local_database_url(active.database_url)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                z.id,
                ST_AsGeoJSON(ST_Transform(z.metric_geometry, 4326), 8)::jsonb,
                ST_AsGeoJSON(ST_Transform(z.metric_geometry, 3857), 3)::jsonb,
                encode(digest(ST_AsEWKB(z.metric_geometry), 'sha256'), 'hex'),
                ST_XMin(ST_Extent(ST_Transform(z.metric_geometry, 4326))),
                ST_YMin(ST_Extent(ST_Transform(z.metric_geometry, 4326))),
                ST_XMax(ST_Extent(ST_Transform(z.metric_geometry, 4326))),
                ST_YMax(ST_Extent(ST_Transform(z.metric_geometry, 4326)))
            FROM segment_zone z
            JOIN road_segment segment ON segment.id = z.road_segment_id
            JOIN road_axis_candidate axis ON axis.id = segment.road_axis_candidate_id
            JOIN road ON road.id = axis.road_id
            WHERE road.code = %s AND segment.segment_index = %s AND z.zone_type = %s
              AND z.data_status = 'prepared' AND NOT z.eligible_for_operations
              AND z.metric_geometry IS NOT NULL
            GROUP BY z.id
            """,
            (arguments.road_code, arguments.segment_index, arguments.zone),
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("prepared non-operational AOI was not found")
    zone_id, geometry_wgs84, geometry_3857, geometry_hash, *bounds = row
    transport = UrllibJsonTransport(timeout_seconds=90)
    tokens = CopernicusTokenProvider(
        active.copernicus_client_id, active.copernicus_client_secret, transport
    )
    provider = SentinelCatalogProvider()
    search = provider.build_search_request(
        BoundingBox(*map(float, bounds)), SearchWindow(start, end), limit=arguments.limit
    )
    page = SentinelCatalogClient(transport, tokens).search(search)
    if not page.acquisitions:
        raise RuntimeError("no Sentinel acquisition was found for the AOI and interval")
    acquisition = min(
        page.acquisitions,
        key=lambda item: item.cloud_cover_percent if item.cloud_cover_percent is not None else 101,
    )
    scene = PostgresSatelliteCatalog(database_url).register(acquisition, datetime.now(UTC))
    day_start = acquisition.acquired_at.astimezone(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    day_end = day_start + timedelta(days=1)
    statistics = SentinelStatisticalClient(transport, tokens).analyze(
        build_statistical_request(geometry_wgs84, day_start, day_end)
    )
    repository = PostgresStatisticalAnalysisRepository(database_url)
    persisted = [
        repository.register_prepared(
            scene_id=scene.id,
            segment_zone_id=zone_id,
            geometry_hash=geometry_hash,
            statistic=item,
        )
        for item in statistics
    ]
    artifacts = SentinelProcessClient(transport, tokens).process(
        build_process_request(geometry_3857, day_start, day_end)
    )
    cache_process_artifacts(database_url, scene.id, geometry_hash, artifacts)
    return {
        "catalog_acquisitions": len(page.acquisitions),
        "scene_created": scene.created,
        "statistics": len(statistics),
        "analysis_created": sum(item.created for item in persisted),
        "geotiff_bytes": len(artifacts.geotiff),
        "result_status": "inconclusive",
        "recommendation": "inspect",
        "operationally_eligible": False,
    }


def main() -> None:
    result = run(build_parser().parse_args())
    print(" ".join(f"{key}={str(value).lower()}" for key, value in result.items()))


if __name__ == "__main__":
    main()
