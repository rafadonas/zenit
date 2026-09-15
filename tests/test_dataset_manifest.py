from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from scripts.verify_dataset_manifest import (
    DatasetManifestError,
    verify_dataset_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
TRACKED_MANIFEST = ROOT / "data/manifests/vegetation-dataset-2026-09-15.json"


def _tracked_payload() -> dict[str, object]:
    return json.loads(TRACKED_MANIFEST.read_text(encoding="utf-8"))


def _write_manifest(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_tracked_manifest_is_explicitly_blocked_and_fail_closed() -> None:
    payload = verify_dataset_manifest(TRACKED_MANIFEST)

    assert payload["status"] == "blocked"
    assert payload["eligibility"]["eligible_for_model_training"] is False  # type: ignore[index]


def test_manifest_rejects_training_source_even_when_gate_is_bypassed(tmp_path: Path) -> None:
    payload = copy.deepcopy(_tracked_payload())
    payload["sources"][0]["included_in_training"] = True  # type: ignore[index]

    with pytest.raises(DatasetManifestError, match="included_in_training"):
        verify_dataset_manifest(_write_manifest(tmp_path / "dataset.json", payload))


def test_manifest_rejects_unsafe_source_path(tmp_path: Path) -> None:
    payload = copy.deepcopy(_tracked_payload())
    payload["sources"][0]["relative_path"] = "../outside.kmz"  # type: ignore[index]

    with pytest.raises(DatasetManifestError, match="relative_path"):
        verify_dataset_manifest(_write_manifest(tmp_path / "dataset.json", payload))


def test_manifest_rejects_adjudicated_status_without_independent_annotation(tmp_path: Path) -> None:
    payload = copy.deepcopy(_tracked_payload())
    payload["labels"]["status"] = "adjudicated"  # type: ignore[index]

    with pytest.raises(DatasetManifestError, match="adjudicated"):
        verify_dataset_manifest(_write_manifest(tmp_path / "dataset.json", payload))


def test_manifest_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    manifest = tmp_path / "dataset.json"
    manifest.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")

    with pytest.raises(DatasetManifestError, match="duplicate JSON key"):
        verify_dataset_manifest(manifest)
