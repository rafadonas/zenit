import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from zenit_geospatial.asset_lineage import (
    AssetRecord,
    AssetUnavailableError,
    AssetUnreadableError,
    build_manifest,
    summarize,
    verify_assets,
)
from zenit_geospatial.asset_lineage_cli import build_parser, run

CONTENT = b"planet-analytic-bytes"
CHECKSUM = hashlib.sha256(CONTENT).hexdigest()
CHECKED_AT = datetime(2026, 9, 15, 12, tzinfo=UTC)


def asset(role: str = "ortho_analytic_4b", checksum: str = CHECKSUM, **overrides) -> AssetRecord:
    values = {
        "id": UUID("45000000-0000-4000-8000-000000000001"),
        "scene_id": UUID("45000000-0000-4000-8000-000000000002"),
        "provider": "planet",
        "external_scene_id": "20260805_135356_12_253c",
        "sensor": "planet-scope",
        "asset_role": role,
        "storage_uri": "s3://zenit-raw/planet/orders/ord-1/asset.aesgcm",
        "checksum_sha256": checksum,
        "media_type": "image/tiff",
        "storage_version_id": "v1",
        "size_bytes": len(CONTENT),
        "order_id": UUID("45000000-0000-4000-8000-000000000003"),
        "external_order_id": "ord-1",
    }
    values.update(overrides)
    return AssetRecord(**values)


class _Reader:
    def __init__(self, content: bytes | Exception = CONTENT) -> None:
        self.content = content
        self.reads: list[tuple[str, str | None]] = []

    def read_plaintext(self, storage_uri: str, version_id: str | None) -> bytes:
        self.reads.append((storage_uri, version_id))
        if isinstance(self.content, Exception):
            raise self.content
        return self.content


class _Lineage:
    def __init__(self, assets: tuple[AssetRecord, ...]) -> None:
        self._assets = assets
        self.recorded: list[tuple[str, str]] = []

    def assets(self) -> tuple[AssetRecord, ...]:
        return self._assets

    def record(self, results, checked_at) -> None:
        assert checked_at.tzinfo is not None
        self.recorded.extend((str(result.asset_id), result.status) for result in results)


def test_matching_bytes_are_verified() -> None:
    results = verify_assets([asset()], _Reader())

    assert results[0].status == "verified"
    assert results[0].observed_checksum == CHECKSUM
    assert results[0].observed_bytes == len(CONTENT)
    assert summarize(results)["all_verified"] is True


def test_changed_bytes_are_reported_as_mismatch_and_not_repaired() -> None:
    results = verify_assets([asset()], _Reader(b"tampered"))
    summary = summarize(results)

    assert results[0].status == "mismatch"
    assert results[0].observed_checksum == hashlib.sha256(b"tampered").hexdigest()
    assert summary["all_verified"] is False
    assert summary["unusable_asset_ids"] == [str(asset().id)]


def test_registered_size_divergence_is_a_mismatch() -> None:
    results = verify_assets([asset(size_bytes=len(CONTENT) + 1)], _Reader())

    assert results[0].status == "mismatch"
    assert "size" in results[0].detail


def test_absent_object_is_missing_and_undecryptable_object_is_unreadable() -> None:
    missing = verify_assets([asset()], _Reader(AssetUnavailableError("not found")))
    unreadable = verify_assets([asset()], _Reader(AssetUnreadableError("bad tag")))

    assert missing[0].status == "missing" and missing[0].observed_checksum is None
    assert unreadable[0].status == "unreadable"
    assert summarize(missing + unreadable)["by_status"] == {
        "verified": 0,
        "mismatch": 0,
        "missing": 1,
        "unreadable": 1,
    }


def test_verify_reads_the_recorded_object_version() -> None:
    reader = _Reader()

    verify_assets([asset()], reader)

    assert reader.reads == [("s3://zenit-raw/planet/orders/ord-1/asset.aesgcm", "v1")]


def test_export_is_deterministic_and_never_official(tmp_path: Path) -> None:
    assets = (asset(role="udm2"), asset(role="ortho_analytic_4b"))

    first = build_manifest(assets, (), generated_at=CHECKED_AT, root=tmp_path)
    second = build_manifest(tuple(reversed(assets)), (), generated_at=CHECKED_AT, root=tmp_path)

    assert first == second
    assert [entry["asset"]["role"] for entry in first["assets"]] == ["ortho_analytic_4b", "udm2"]
    assert first["eligible_for_official_reporting"] is False
    assert first["derived_artifacts"] == []


def test_export_links_derived_artifacts_to_their_source(tmp_path: Path) -> None:
    preview = tmp_path / "docs/previews/sentinel-ndvi-preview.html"
    preview.parent.mkdir(parents=True)
    preview.write_text("<html>preview</html>", encoding="utf-8")
    manifest_path = tmp_path / "data/manifests/sentinel-ndvi-preview.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "processor_version": "zenit-cached-ndvi-preview-v1",
                "result_status": "inconclusive",
                "source": {"sha256": "a" * 64},
                "artifact": {
                    "relative_path": "docs/previews/sentinel-ndvi-preview.html",
                    "sha256": hashlib.sha256(b"<html>preview</html>").hexdigest(),
                },
                "dashboard_layer": {
                    "relative_path": "apps/dashboard/src/data/cached-ndvi-preview.json",
                    "sha256": "b" * 64,
                },
            }
        ),
        encoding="utf-8",
    )

    derived = build_manifest((), (), generated_at=CHECKED_AT, root=tmp_path)["derived_artifacts"]

    assert derived[0]["role"] == "artifact"
    assert derived[0]["matches"] is True
    assert derived[0]["parent_source_sha256"] == "a" * 64
    assert derived[1]["role"] == "dashboard_layer"
    assert derived[1]["observed_sha256"] is None
    assert derived[1]["matches"] is False


def test_cli_verify_appends_audit_records(tmp_path: Path) -> None:
    lineage = _Lineage((asset(),))

    report = run(
        build_parser().parse_args(["--verify"]),
        lineage=lineage,
        reader=_Reader(),
        now=CHECKED_AT,
        root=tmp_path,
    )

    assert report["all_verified"] is True
    assert report["recorded"] is True
    assert lineage.recorded == [(str(asset().id), "verified")]


def test_cli_dry_run_reports_without_recording(tmp_path: Path) -> None:
    lineage = _Lineage((asset(),))

    report = run(
        build_parser().parse_args(["--verify", "--dry-run"]),
        lineage=lineage,
        reader=_Reader(b"tampered"),
        now=CHECKED_AT,
        root=tmp_path,
    )

    assert report["by_status"]["mismatch"] == 1
    assert report["recorded"] is False
    assert lineage.recorded == []


def test_cli_export_does_not_touch_object_storage(tmp_path: Path) -> None:
    lineage = _Lineage((asset(),))
    reader = _Reader()

    manifest = run(
        build_parser().parse_args(["--export"]),
        lineage=lineage,
        reader=reader,
        now=CHECKED_AT,
        root=tmp_path,
    )

    assert manifest["assets"][0]["asset"]["checksum_sha256"] == CHECKSUM
    assert reader.reads == []
    assert lineage.recorded == []


def test_cli_requires_one_mode() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
