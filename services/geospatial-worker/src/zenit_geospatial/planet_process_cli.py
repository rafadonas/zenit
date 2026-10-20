"""Process the 1 km pilot stretch offline from cached, verified Planet assets.

The command never calls the provider: it reads bytes from local storage and
geometry from the local database. Results stay inconclusive and non-operational.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any

from zenit_api.config import Settings
from zenit_geospatial.asset_lineage import AssetReader
from zenit_geospatial.database_target import resolve_database_url
from zenit_geospatial.planet_process import (
    ProcessingError,
    explanation,
    geometry_hash,
    idempotency_key,
    summarize,
    zone_statistics,
)
from zenit_geospatial.planet_process_repository import PostgresPilotProcessing

PILOT_SEGMENTS = 10  # 10 segments of 100 m = the approved 1 km pilot stretch
ANALYTIC_ROLE_PREFIX = "ortho_analytic"
UDM2_ROLE_PREFIX = "udm2"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zenit-planet-process",
        description="Offline NDVI statistics per zone for the 1 km pilot stretch",
    )
    parser.add_argument("--scene-id", required=True, help="external Planet scene identifier")
    parser.add_argument("--road-code", default="SP021")
    parser.add_argument("--from-segment", type=int, required=True)
    parser.add_argument(
        "--segments",
        type=int,
        default=PILOT_SEGMENTS,
        help=f"number of 100 m segments to process (default {PILOT_SEGMENTS} = 1 km)",
    )
    parser.add_argument(
        "--database-url",
        help="explicit database; required when the configured host is Compose-only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="compute and report without writing analysis results",
    )
    return parser


def run(
    arguments: argparse.Namespace,
    settings: Settings | None = None,
    *,
    repository: PostgresPilotProcessing | None = None,
    reader: AssetReader | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if arguments.segments < 1:
        raise ValueError("segments must be positive")
    active = settings or Settings()
    store = repository or PostgresPilotProcessing(
        resolve_database_url(arguments.database_url, active.database_url)
    )
    scene = store.scene(arguments.scene_id)
    analytic_asset = scene.asset(ANALYTIC_ROLE_PREFIX)
    udm2_asset = scene.asset(UDM2_ROLE_PREFIX)
    for asset in (analytic_asset, udm2_asset):
        if asset.verification_status != "verified":
            raise ProcessingError(
                f"asset {asset.asset_role!r} is {asset.verification_status or 'unverified'}; "
                "run zenit-asset-lineage --verify before processing"
            )

    zones = store.pilot_zones(
        road_code=arguments.road_code,
        from_segment=arguments.from_segment,
        to_segment=arguments.from_segment + arguments.segments - 1,
    )
    if not zones:
        raise LookupError("no zone geometry found for the requested pilot stretch")
    operational = [zone for zone in zones if zone.eligible_for_operations]
    if operational:
        raise ProcessingError("pilot processing refuses zones flagged as operational")

    if reader is None:
        from zenit_geospatial.satellite_storage import EncryptedSatelliteStore

        reader = EncryptedSatelliteStore(active)
    analytic = reader.read_plaintext(analytic_asset.storage_uri, analytic_asset.storage_version_id)
    udm2 = reader.read_plaintext(udm2_asset.storage_uri, udm2_asset.storage_version_id)

    results = []
    persisted = 0
    skipped: list[dict[str, Any]] = []
    for zone in zones:
        try:
            statistics = zone_statistics(
                segment_zone_id=zone.id,
                analytic=analytic,
                udm2=udm2,
                geometry=zone.geometry,
            )
        except ProcessingError as error:
            skipped.append(
                {"segment_index": zone.segment_index, "zone": zone.zone_type, "reason": str(error)}
            )
            continue
        results.append(statistics)
        if arguments.dry_run:
            continue
        zone_hash = geometry_hash(zone.geometry)
        created = store.persist(
            scene_id=scene.id,
            statistics=statistics,
            idempotency_key=idempotency_key(
                scene_id=scene.id,
                segment_zone_id=zone.id,
                analytic_checksum=analytic_asset.checksum_sha256,
                udm2_checksum=udm2_asset.checksum_sha256,
                geometry_hash=zone_hash,
            ),
            parameters={
                "road_code": arguments.road_code,
                "segment_index": zone.segment_index,
                "zone_type": zone.zone_type,
                "scene": scene.external_scene_id,
                "offline": True,
                "generated_at": (now or datetime.now(UTC)).isoformat(),
            },
            explanation=explanation(
                statistics,
                analytic_checksum=analytic_asset.checksum_sha256,
                udm2_checksum=udm2_asset.checksum_sha256,
                geometry_hash_value=zone_hash,
                zone_data_status=zone.data_status,
            ),
        )
        persisted += int(created)

    report = summarize(results)
    report["scene"] = scene.external_scene_id
    report["road_code"] = arguments.road_code
    report["segments"] = arguments.segments
    report["analysis_runs_created"] = persisted
    report["persisted"] = not arguments.dry_run
    report["skipped_zones"] = skipped
    return report


def main(argv: list[str] | None = None) -> None:
    arguments = build_parser().parse_args(argv)
    try:
        report = run(arguments)
    except (LookupError, OSError, ProcessingError, RuntimeError, ValueError) as error:
        raise SystemExit(f"zenit-planet-process: {error}") from None
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
