from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from scripts.verify_release_evidence import ReleaseEvidenceError, verify_release_evidence

ROOT = Path(__file__).resolve().parents[1]
TRACKED_EVIDENCE = (
    ROOT / "docs/release-evidence/android-mvp-debug-apk-2026-08-14.json"
)


def _tracked_payload() -> dict[str, object]:
    return json.loads(TRACKED_EVIDENCE.read_text(encoding="utf-8"))


def _write_manifest(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_tracked_android_release_evidence_satisfies_non_operational_contract() -> None:
    payload = verify_release_evidence(TRACKED_EVIDENCE)

    assert payload["schema_version"] == 1


def test_release_evidence_rejects_operational_scope(tmp_path: Path) -> None:
    payload = copy.deepcopy(_tracked_payload())
    payload["scope"]["eligible_for_field_execution"] = True  # type: ignore[index]

    with pytest.raises(ReleaseEvidenceError, match="eligible_for_field_execution"):
        verify_release_evidence(_write_manifest(tmp_path / "evidence.json", payload))


def test_release_evidence_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    manifest = tmp_path / "evidence.json"
    manifest.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")

    with pytest.raises(ReleaseEvidenceError, match="duplicate JSON key"):
        verify_release_evidence(manifest)


def test_release_evidence_rejects_mismatched_verifier_revision(tmp_path: Path) -> None:
    payload = copy.deepcopy(_tracked_payload())
    payload["verification"]["verifier_revision"] = "deadbee"  # type: ignore[index]

    with pytest.raises(ReleaseEvidenceError, match=r"verification\.verifier_revision"):
        verify_release_evidence(_write_manifest(tmp_path / "evidence.json", payload))


def test_release_evidence_checks_supplied_artifact_hash(tmp_path: Path) -> None:
    payload = copy.deepcopy(_tracked_payload())
    artifact = tmp_path / "app-debug.apk"
    artifact_bytes = b"not the tracked artifact"
    artifact.write_bytes(artifact_bytes)
    payload["artifact"]["size_bytes"] = len(artifact_bytes)  # type: ignore[index]
    manifest = _write_manifest(tmp_path / "evidence.json", payload)

    with pytest.raises(ReleaseEvidenceError, match="APK SHA-256 does not match"):
        verify_release_evidence(manifest, artifact_path=artifact)
