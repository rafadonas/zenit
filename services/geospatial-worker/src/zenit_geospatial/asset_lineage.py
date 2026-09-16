"""PLANET-007: integrity audit and lineage export for stored satellite assets.

The audit only reads: a divergence is recorded as evidence and never repaired
automatically. Lineage stays where the entity lives (scene, order, asset); the
``data_lineage`` table is reserved for imported source files, whose parent is a
``source_file`` or ``import_run`` that a provider asset does not have.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

import psycopg

VERIFIER_VERSION = "zenit-asset-verifier-v1"
DERIVED_MANIFESTS = (Path("data/manifests/sentinel-ndvi-preview.json"),)


class AssetUnavailableError(RuntimeError):
    """Raised by a reader when the stored object cannot be found."""


class AssetUnreadableError(RuntimeError):
    """Raised by a reader when the stored object cannot be decoded or decrypted."""


class AssetReader(Protocol):
    def read_plaintext(self, storage_uri: str, version_id: str | None) -> bytes: ...


@dataclass(frozen=True, slots=True)
class AssetRecord:
    id: UUID
    scene_id: UUID
    provider: str
    external_scene_id: str
    sensor: str
    asset_role: str
    storage_uri: str
    checksum_sha256: str
    media_type: str
    storage_version_id: str | None
    size_bytes: int | None
    order_id: UUID | None
    external_order_id: str | None


@dataclass(frozen=True, slots=True)
class VerificationResult:
    asset_id: UUID
    status: str
    expected_checksum: str
    observed_checksum: str | None
    observed_bytes: int | None
    detail: str | None

    @property
    def ok(self) -> bool:
        return self.status == "verified"


def verify_asset(asset: AssetRecord, reader: AssetReader) -> VerificationResult:
    try:
        content = reader.read_plaintext(asset.storage_uri, asset.storage_version_id)
    except AssetUnavailableError as error:
        return VerificationResult(
            asset.id, "missing", asset.checksum_sha256, None, None, str(error)
        )
    except AssetUnreadableError as error:
        return VerificationResult(
            asset.id, "unreadable", asset.checksum_sha256, None, None, str(error)
        )
    observed = hashlib.sha256(content).hexdigest()
    if observed != asset.checksum_sha256:
        return VerificationResult(
            asset.id,
            "mismatch",
            asset.checksum_sha256,
            observed,
            len(content),
            "stored bytes do not match the registered checksum",
        )
    if asset.size_bytes is not None and asset.size_bytes != len(content):
        return VerificationResult(
            asset.id,
            "mismatch",
            asset.checksum_sha256,
            observed,
            len(content),
            "stored size does not match the registered size",
        )
    return VerificationResult(
        asset.id, "verified", asset.checksum_sha256, observed, len(content), None
    )


def verify_assets(
    assets: Sequence[AssetRecord], reader: AssetReader
) -> tuple[VerificationResult, ...]:
    return tuple(verify_asset(asset, reader) for asset in assets)


def summarize(results: Iterable[VerificationResult]) -> dict[str, object]:
    counts = {"verified": 0, "mismatch": 0, "missing": 0, "unreadable": 0}
    unusable: list[str] = []
    for result in results:
        counts[result.status] += 1
        if not result.ok:
            unusable.append(str(result.asset_id))
    return {
        "verifier_version": VERIFIER_VERSION,
        "checked": sum(counts.values()),
        "by_status": counts,
        "unusable_asset_ids": sorted(unusable),
        "all_verified": not unusable,
    }


def derived_artifacts(root: Path = Path(".")) -> list[dict[str, object]]:
    """Derived products declared in repository manifests, linked by source checksum."""
    artifacts: list[dict[str, object]] = []
    for manifest_path in DERIVED_MANIFESTS:
        path = root / manifest_path
        if not path.exists():
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        source = manifest.get("source", {})
        for key in ("artifact", "dashboard_layer"):
            entry = manifest.get(key)
            if not isinstance(entry, dict):
                continue
            relative = entry.get("relative_path")
            declared = entry.get("sha256")
            target = root / str(relative)
            observed = (
                hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
            )
            artifacts.append(
                {
                    "manifest": str(manifest_path),
                    "role": key,
                    "relative_path": relative,
                    "declared_sha256": declared,
                    "observed_sha256": observed,
                    "matches": observed == declared,
                    "parent_source_sha256": source.get("sha256"),
                    "processor_version": manifest.get("processor_version"),
                    "result_status": manifest.get("result_status"),
                }
            )
    return artifacts


def build_manifest(
    assets: Sequence[AssetRecord],
    results: Sequence[VerificationResult],
    *,
    generated_at: datetime,
    root: Path = Path("."),
) -> dict[str, object]:
    """Deterministic export: same database state always yields the same document."""
    status_by_asset = {result.asset_id: result for result in results}
    entries = []
    for asset in sorted(assets, key=lambda item: (item.external_scene_id, item.asset_role)):
        result = status_by_asset.get(asset.id)
        entries.append(
            {
                "scene": {
                    "provider": asset.provider,
                    "external_scene_id": asset.external_scene_id,
                    "sensor": asset.sensor,
                },
                "order": {"external_order_id": asset.external_order_id},
                "asset": {
                    "role": asset.asset_role,
                    "storage_uri": asset.storage_uri,
                    "storage_version_id": asset.storage_version_id,
                    "checksum_sha256": asset.checksum_sha256,
                    "media_type": asset.media_type,
                    "size_bytes": asset.size_bytes,
                },
                "verification": None
                if result is None
                else {"status": result.status, "observed_bytes": result.observed_bytes},
            }
        )
    return {
        "verifier_version": VERIFIER_VERSION,
        "generated_at": generated_at.isoformat(),
        "assets": entries,
        "derived_artifacts": derived_artifacts(root),
        "eligible_for_official_reporting": False,
    }


class PostgresAssetLineage:
    """Reads assets with their lineage and appends immutable verification records."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def assets(self) -> tuple[AssetRecord, ...]:
        query = """
            SELECT asset.id, scene.id, scene.provider, scene.external_scene_id, scene.sensor,
                   asset.asset_role, asset.storage_uri, asset.checksum_sha256, asset.media_type,
                   asset.storage_version_id, asset.size_bytes,
                   asset.source_order_id, planet.external_order_id
            FROM satellite_asset asset
            JOIN satellite_scene scene ON scene.id = asset.satellite_scene_id
            LEFT JOIN planet_order planet ON planet.id = asset.source_order_id
            ORDER BY scene.external_scene_id, asset.asset_role
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return tuple(
            AssetRecord(
                id=row[0],
                scene_id=row[1],
                provider=row[2],
                external_scene_id=row[3],
                sensor=row[4],
                asset_role=row[5],
                storage_uri=row[6],
                checksum_sha256=row[7],
                media_type=row[8],
                storage_version_id=row[9],
                size_bytes=row[10],
                order_id=row[11],
                external_order_id=row[12],
            )
            for row in rows
        )

    def record(self, results: Sequence[VerificationResult], checked_at: datetime) -> None:
        if checked_at.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware")
        insert = """
            INSERT INTO satellite_asset_verification (
                satellite_asset_id, checked_at, expected_checksum_sha256,
                observed_checksum_sha256, observed_bytes, status, detail, verifier_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            for result in results:
                cursor.execute(
                    insert,
                    (
                        result.asset_id,
                        checked_at,
                        result.expected_checksum,
                        result.observed_checksum,
                        result.observed_bytes,
                        result.status,
                        result.detail,
                        VERIFIER_VERSION,
                    ),
                )
