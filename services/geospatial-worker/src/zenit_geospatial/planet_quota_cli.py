"""Report the approved Planet budget and what the recorded Orders already consumed."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime

from zenit_api.config import Settings
from zenit_geospatial.database_target import resolve_database_url
from zenit_geospatial.planet_quota import PostgresPlanetQuota, QuotaError, QuotaStatus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zenit-planet-quota",
        description="Report the approved Planet quota budget and its recorded consumption",
    )
    parser.add_argument(
        "--database-url",
        help="explicit database; required when the configured host is Compose-only",
    )
    parser.add_argument(
        "--at",
        type=datetime.fromisoformat,
        help="instant to report, ISO-8601 with offset (default: now, UTC)",
    )
    return parser


def run(
    arguments: argparse.Namespace,
    settings: Settings | None = None,
    *,
    quota_status: QuotaStatus | None = None,
) -> dict[str, object]:
    at = arguments.at or datetime.now(UTC)
    if at.tzinfo is None:
        raise ValueError("--at must include a UTC offset")
    if quota_status is not None:
        return quota_status.as_report()
    active = settings or Settings()
    database_url = resolve_database_url(arguments.database_url, active.database_url)
    return PostgresPlanetQuota(database_url).status(at).as_report()


def main(argv: list[str] | None = None) -> None:
    try:
        report = run(build_parser().parse_args(argv))
    except (QuotaError, RuntimeError, ValueError) as error:
        raise SystemExit(f"zenit-planet-quota: {error}") from None
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
