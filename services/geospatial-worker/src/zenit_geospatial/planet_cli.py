"""Discover PlanetScope scenes without ordering assets or consuming download quota."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta

from zenit_api.config import Settings
from zenit_geospatial.satellite_http import PlanetCatalogClient, UrllibJsonTransport
from zenit_geospatial.satellite_providers import BoundingBox, PlanetDataProvider, SearchWindow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover Planet PSScene metadata for a prepared, non-operational AOI"
    )
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        required=True,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
    )
    parser.add_argument("--from-date", type=date.fromisoformat, required=True)
    parser.add_argument("--to-date", type=date.fromisoformat, required=True)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--require-download-permission",
        action="store_true",
        help="include only scenes with the assets:download permission",
    )
    return parser


def run(arguments: argparse.Namespace, settings: Settings | None = None) -> dict[str, object]:
    active = settings or Settings()
    if active.planet_api_key is None:
        raise RuntimeError("Planet API key is not configured")
    start = datetime.combine(arguments.from_date, datetime.min.time(), tzinfo=UTC)
    end = datetime.combine(arguments.to_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    if start >= end:
        raise ValueError("from-date must not be after to-date")

    require_download_permission = bool(
        getattr(arguments, "require_download_permission", False)
    )
    provider = PlanetDataProvider()
    payload = provider.build_search_request(
        BoundingBox(*arguments.bbox),
        SearchWindow(start, end),
        limit=arguments.limit,
        require_download_permission=require_download_permission,
    )
    page = PlanetCatalogClient(
        UrllibJsonTransport(timeout_seconds=30),
        active.planet_api_key.get_secret_value(),
        provider,
    ).search(payload)
    return {
        "catalog_acquisitions": len(page.acquisitions),
        "has_next_page": page.next_url is not None,
        "download_requested": False,
        "operationally_eligible": False,
        "download_permission_filter": require_download_permission,
    }


def main() -> None:
    result = run(build_parser().parse_args())
    print(" ".join(f"{key}={str(value).lower()}" for key, value in result.items()))


if __name__ == "__main__":
    main()
