from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from scripts.generate_simulated_mowing_timeseries import (
    ZONE_TYPES,
    ScenarioConfig,
    build_manifest,
    build_records,
    render_csv,
    validate,
    write_dataset,
)


def test_builds_six_month_scenario_for_each_independent_zone() -> None:
    config = ScenarioConfig()
    records = build_records(config)

    assert len(records) == 720
    assert {(record["zone_type"], record["scenario_date"]) for record in records} == {
        (zone, (date(2026, 8, 1) + timedelta(days=day)).isoformat())
        for zone in ZONE_TYPES
        for day in range(180)
    }
    special_thresholds = {
        record["threshold_cm"] for record in records if record["zone_type"] == "special"
    }
    assert special_thresholds == {10}
    assert {
        record["threshold_cm"] for record in records if record["zone_type"] != "special"
    } == {30}


def test_scripted_mowing_events_reset_height_without_authorizing_work() -> None:
    records = build_records(ScenarioConfig())
    events = [record for record in records if record["simulated_mowing_event"]]

    assert len(events) == 25
    assert [(event["zone_type"], event["scenario_date"]) for event in events[:4]] == [
        ("left", "2026-08-13"),
        ("left", "2026-09-24"),
        ("left", "2026-11-05"),
        ("left", "2026-12-17"),
    ]
    assert [
        event["scenario_date"] for event in events if event["zone_type"] == "special"
    ][-1] == "2027-01-24"
    assert all(
        event["simulated_height_after_mowing_cm"]
        < event["simulated_height_before_mowing_cm"]
        for event in events
    )
    assert all(event["authorizes_mowing"] is False for event in events)


def test_every_record_is_simulated_and_training_ineligible() -> None:
    records = build_records(ScenarioConfig())
    csv_text = render_csv(records)
    manifest = build_manifest(ScenarioConfig(), records, csv_text)

    validate(records, manifest, csv_text)
    for record in records:
        assert record["data_status"] == "simulated"
        assert record["eligible_for_model_training"] is False
        assert record["eligible_for_official_reporting"] is False
        assert record["eligible_for_operations"] is False
        assert record["authorizes_mowing"] is False
    assert set(manifest["eligibility"].values()) == {False}


def test_generation_is_deterministic_and_seeded() -> None:
    first = render_csv(build_records(ScenarioConfig(seed=7)))
    second = render_csv(build_records(ScenarioConfig(seed=7)))
    different = render_csv(build_records(ScenarioConfig(seed=8)))

    assert first == second
    assert first != different


def test_csv_is_machine_readable_and_checksum_bound() -> None:
    records = build_records(ScenarioConfig(days=3))
    csv_text = render_csv(records)
    manifest = build_manifest(ScenarioConfig(days=3), records, csv_text)
    parsed = list(csv.DictReader(io.StringIO(csv_text)))

    assert len(parsed) == 12
    assert parsed[0]["data_status"] == "simulated"
    assert parsed[0]["eligible_for_model_training"] == "False"
    assert manifest["checksums"]["csv_sha256"] == hashlib.sha256(csv_text.encode()).hexdigest()


def test_validation_rejects_training_eligibility() -> None:
    records = build_records(ScenarioConfig(days=2))
    csv_text = render_csv(records)
    manifest = build_manifest(ScenarioConfig(days=2), records, csv_text)
    records[0]["eligible_for_model_training"] = True

    with pytest.raises(ValueError, match="eligible_for_model_training must remain false"):
        validate(records, manifest, csv_text)


def test_writer_refuses_raw_and_writes_reproducible_artifacts(tmp_path: Path) -> None:
    raw = tmp_path / "data" / "raw"
    with pytest.raises(ValueError, match="must never be written under data/raw"):
        write_dataset(ScenarioConfig(days=2), raw / "scenario", tmp_path)

    output = tmp_path / "data" / "simulated" / "scenario"
    csv_path, manifest_path = write_dataset(ScenarioConfig(days=2), output, tmp_path)
    first_csv = csv_path.read_bytes()
    first_manifest = manifest_path.read_bytes()
    write_dataset(ScenarioConfig(days=2), output, tmp_path)

    assert csv_path.read_bytes() == first_csv
    assert manifest_path.read_bytes() == first_manifest
    assert json.loads(first_manifest)["data_status"] == "simulated"


def test_committed_presentation_artifacts_are_reproducible() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    output = repository_root / "data" / "simulated" / "sp021-195"
    csv_path = output / "mowing-timeseries.csv"
    manifest_path = output / "mowing-timeseries.manifest.json"
    expected_records = build_records(ScenarioConfig())
    expected_csv = render_csv(expected_records)
    expected_manifest = build_manifest(ScenarioConfig(), expected_records, expected_csv)

    assert csv_path.read_text(encoding="utf-8") == expected_csv
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == expected_manifest
    assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == (
        "8fa4ce5b6de213ad03db6a22032cf3caf4da9a03768b043b598671489c92a1ed"
    )
