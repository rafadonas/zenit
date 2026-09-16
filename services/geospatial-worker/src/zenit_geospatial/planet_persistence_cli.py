"""Persist bounded Planet catalog metadata without ordering or downloading assets."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlsplit

from zenit_api.config import Settings
from zenit_geospatial.satellite_catalog import PostgresSatelliteCatalog
from zenit_geospatial.satellite_http import PlanetCatalogClient, UrllibJsonTransport
from zenit_geospatial.satellite_providers import BoundingBox, PlanetDataProvider, SearchWindow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persist bounded Planet PSScene metadata with download permission"
    )
    parser.add_argument("--bbox", nargs=4, type=float, required=True,
                        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"))
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--to-date", type=date.fromisoformat, required=True)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--database-url",
        help="explicit destination database; required when the configured host is Compose-only",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="confirm writing normalized metadata to the configured local database",
    )
    return parser


COMPOSE_ONLY_HOSTS = ("postgres",)


def resolve_database_url(requested: str | None, configured: str) -> str:
    """Never rewrite the host implicitly: a wrong guess writes to another database."""

    url = (requested or configured).replace("postgresql+psycopg://", "postgresql://", 1)
    host = urlsplit(url).hostname
    if requested is None and host in COMPOSE_ONLY_HOSTS:
        raise RuntimeError(
            f"configured database host {host!r} is only reachable inside Compose; "
            "pass --database-url with the ZENIT database reachable from here"
        )
    return url


def run(
    arguments: argparse.Namespace,
    settings: Settings | None = None,
    *,
    client: PlanetCatalogClient | None = None,
    catalog: PostgresSatelliteCatalog | None = None,
) -> dict[str, object]:
    if not arguments.persist:
        raise RuntimeError("metadata persistence requires the --persist confirmation")
    active = settings or Settings()
    if active.planet_api_key is None:
        raise RuntimeError("Planet API key is not configured")
    database_url = resolve_database_url(arguments.database_url, active.database_url)
    start = datetime.combine(arguments.from_date, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(arguments.to_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    if start >= end:
        raise ValueError("from-date must not be after to-date")

    provider = PlanetDataProvider()
    payload = provider.build_search_request(
        BoundingBox(*arguments.bbox),
        SearchWindow(start, end),
        limit=arguments.limit,
        require_download_permission=True,
    )
    search_client = client or PlanetCatalogClient(
        UrllibJsonTransport(timeout_seconds=30),
        active.planet_api_key.get_secret_value(),
        provider,
    )
    page = search_client.search(payload)
    if not page.acquisitions:
        return {
            "catalog_acquisitions": 0,
            "scenes_created": 0,
            "scenes_existing": 0,
            "has_next_page": page.next_url is not None,
            "order_requested": False,
            "download_requested": False,
            "operationally_eligible": False,
        }

    destination = catalog or PostgresSatelliteCatalog(database_url)
    discovered_at = datetime.now(UTC)
    created = 0
    existing = 0
    for acquisition in page.acquisitions:
        result = destination.register(acquisition, discovered_at)
        if result.created:
            created += 1
        else:
            existing += 1
    return {
        "catalog_acquisitions": len(page.acquisitions),
        "scenes_created": created,
        "scenes_existing": existing,
        "has_next_page": page.next_url is not None,
        "order_requested": False,
        "download_requested": False,
        "operationally_eligible": False,
    }


def main() -> None:
    result = run(build_parser().parse_args())
    print(" ".join(f"{key}={str(value).lower()}" for key, value in result.items()))


if __name__ == "__main__":
    main()
