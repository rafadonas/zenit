from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

import pytest
from scripts.build_simulated_feature_snapshots import (
    FEATURE_DEFINITION_VERSION,
    build_feature_snapshots,
    build_manifest,
    load_source,
    render_csv,
    validate_output,
    write_feature_snapshots,
)
from scripts.generate_simulated_mowing_timeseries import (
    ScenarioConfig,
    build_records,
)
from scripts.generate_simulated_mowing_timeseries import (
    build_manifest as build_source_manifest,
)
from scripts.generate_simulated_mowing_timeseries import (
    render_csv as render_source_csv,
)


def _source(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    records = build_records(ScenarioConfig())
    csv_text = render_source_csv(records)
    manifest = build_source_manifest(ScenarioConfig(), records, csv_text)
    csv_path = tmp_path / "mowing.csv"
    manifest_path = tmp_path / "mowing.manifest.json"
    csv_path.write_text(csv_text, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return csv_path, manifest_path


def test_builds_past_only_snapshots_after_fourteen_day_warmup(tmp_path: Path) -> None:
    csv_path, manifest_path = _source(tmp_path)
    records, _ = load_source(csv_path, manifest_path)
    snapshots = build_feature_snapshots(records)

    assert len(snapshots) == 664
    assert snapshots[0]["as_of_date"] == "2026-08-15"
    assert snapshots[-1]["as_of_date"] == "2027-01-27"
    assert {snapshot["zone_type"] for snapshot in snapshots} == {
        "left",
        "right",
        "median",
        "special",
    }
    first_left = next(snapshot for snapshot in snapshots if snapshot["zone_type"] == "left")
    left_sources = [record for record in records if record["zone_type"] == "left"]
    assert first_left["simulated_height_lag_14d_cm"] == float(
        left_sources[0]["simulated_height_after_mowing_cm"]
    )
    assert len(first_left["source_record_ids"].split("|")) == 15
    assert all(source["scenario_date"] <= first_left["as_of_date"] for source in left_sources[:15])


def test_preserves_thresholds_classes_and_non_operational_flags(tmp_path: Path) -> None:
    csv_path, manifest_path = _source(tmp_path)
    records, _ = load_source(csv_path, manifest_path)
    snapshots = build_feature_snapshots(records)

    special_thresholds = {
        row["applicable_threshold_cm"] for row in snapshots if row["zone_type"] == "special"
    }
    general_thresholds = {
        row["applicable_threshold_cm"] for row in snapshots if row["zone_type"] != "special"
    }
    assert special_thresholds == {10}
    assert general_thresholds == {30}
    assert {row["simulated_historical_class"] for row in snapshots} == {"N1", "N2", "N3"}
    assert all(row["feature_definition_version"] == FEATURE_DEFINITION_VERSION for row in snapshots)
    assert all(row["data_status"] == "simulated" for row in snapshots)
    assert all(row["eligible_for_model_training"] is False for row in snapshots)
    assert all(row["authorizes_mowing"] is False for row in snapshots)


def test_split_is_chronological_and_only_a_rehearsal(tmp_path: Path) -> None:
    csv_path, manifest_path = _source(tmp_path)
    records, source_manifest = load_source(csv_path, manifest_path)
    snapshots = build_feature_snapshots(records)
    manifest = build_manifest(snapshots, render_csv(snapshots), source_manifest)

    dates_by_role = {
        role: {row["as_of_date"] for row in snapshots if row["rehearsal_split_role"] == role}
        for role in manifest["rehearsal_split_counts"]
    }
    assert max(dates_by_role["development_rehearsal"]) < min(dates_by_role["validation_rehearsal"])
    assert max(dates_by_role["validation_rehearsal"]) < min(dates_by_role["holdout_rehearsal"])
    assert manifest["eligibility"]["model_fitted"] is False
    assert "single simulated segment" in " ".join(manifest["limitations"]).lower()


def test_rejects_tampered_or_training_eligible_source(tmp_path: Path) -> None:
    csv_path, manifest_path = _source(tmp_path)
    csv_path.write_text(csv_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        load_source(csv_path, manifest_path)

    csv_path, manifest_path = _source(tmp_path / "second")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["eligibility"]["eligible_for_model_training"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="eligible_for_model_training must remain false"):
        load_source(csv_path, manifest_path)


def test_output_is_deterministic_checksum_bound_and_refuses_raw(tmp_path: Path) -> None:
    csv_path, manifest_path = _source(tmp_path)
    raw_output = tmp_path / "data" / "raw" / "features"
    with pytest.raises(ValueError, match="must never be written under data/raw"):
        write_feature_snapshots(csv_path, manifest_path, raw_output, tmp_path)

    output = tmp_path / "data" / "simulated" / "features"
    feature_csv, feature_manifest = write_feature_snapshots(
        csv_path, manifest_path, output, tmp_path
    )
    first_csv = feature_csv.read_bytes()
    first_manifest = feature_manifest.read_bytes()
    write_feature_snapshots(csv_path, manifest_path, output, tmp_path)
    payload = json.loads(first_manifest)

    assert feature_csv.read_bytes() == first_csv
    assert feature_manifest.read_bytes() == first_manifest
    assert payload["checksums"]["csv_sha256"] == hashlib.sha256(first_csv).hexdigest()
    assert len(list(csv.DictReader(io.StringIO(first_csv.decode())))) == 664


def test_validation_rejects_any_output_eligibility(tmp_path: Path) -> None:
    csv_path, manifest_path = _source(tmp_path)
    records, source_manifest = load_source(csv_path, manifest_path)
    snapshots = build_feature_snapshots(records)
    csv_text = render_csv(snapshots)
    manifest = build_manifest(snapshots, csv_text, source_manifest)
    snapshots[0]["eligible_for_model_training"] = True

    with pytest.raises(ValueError, match="eligible_for_model_training must remain false"):
        validate_output(snapshots, manifest, csv_text)


def test_committed_feature_artifacts_are_reproducible() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    scenario = repository_root / "data" / "simulated" / "sp021-195"
    records, source_manifest = load_source(
        scenario / "mowing-timeseries.csv", scenario / "mowing-timeseries.manifest.json"
    )
    snapshots = build_feature_snapshots(records)
    expected_csv = render_csv(snapshots)
    expected_manifest = build_manifest(snapshots, expected_csv, source_manifest)

    assert (scenario / "feature-snapshots.csv").read_text(encoding="utf-8") == expected_csv
    assert (
        json.loads((scenario / "feature-snapshots.manifest.json").read_text(encoding="utf-8"))
        == expected_manifest
    )
    assert hashlib.sha256(expected_csv.encode()).hexdigest() == (
        "51110dd0847063019b82945b77b9f338d0418929ee49cf9ca7b1f9978b352f87"
    )
