"""Audit stored satellite assets and export their lineage (PLANET-007).

``--verify`` only reads the objects and appends immutable audit records; it never
edits or deletes an asset. ``--export`` writes nothing at all.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from zenit_api.config import Settings
from zenit_geospatial.asset_lineage import (
    AssetReader,
    PostgresAssetLineage,
    build_manifest,
    summarize,
    verify_assets,
)
from zenit_geospatial.database_target import resolve_database_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zenit-asset-lineage",
        description="Verify stored satellite asset checksums and export their lineage",
    )
    parser.add_argument(
        "--database-url",
        help="explicit database; required when the configured host is Compose-only",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--verify",
        action="store_true",
        help="recompute checksums from storage and append audit records",
    )
    mode.add_argument(
        "--export",
        action="store_true",
        help="print the lineage manifest without reading object storage",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="with --verify, report findings without appending audit records",
    )
    return parser


def run(
    arguments: argparse.Namespace,
    settings: Settings | None = None,
    *,
    lineage: PostgresAssetLineage | None = None,
    reader: AssetReader | None = None,
    now: datetime | None = None,
    root: Path = Path("."),
) -> dict[str, object]:
    active = settings or Settings()
    store = lineage or PostgresAssetLineage(
        resolve_database_url(arguments.database_url, active.database_url)
    )
    assets = store.assets()
    checked_at = now or datetime.now(UTC)

    if arguments.export:
        return build_manifest(assets, (), generated_at=checked_at, root=root)

    if reader is None:
        from zenit_geospatial.satellite_storage import EncryptedSatelliteStore

        reader = EncryptedSatelliteStore(active)
    results = verify_assets(assets, reader)
    if not arguments.dry_run:
        store.record(results, checked_at)
    report = summarize(results)
    report["recorded"] = not arguments.dry_run
    report["checked_at"] = checked_at.isoformat()
    return report


def main(argv: list[str] | None = None) -> None:
    arguments = build_parser().parse_args(argv)
    try:
        report = run(arguments)
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"zenit-asset-lineage: {error}") from None
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    if arguments.verify and not report.get("all_verified", False):
        raise SystemExit("zenit-asset-lineage: at least one asset is not usable")


if __name__ == "__main__":
    main()
