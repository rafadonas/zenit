#!/usr/bin/env python3
"""Validate versioned vegetation dataset manifests without opening dataset bytes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
SAFE_RELATIVE_PATH = re.compile(r"^[^/].*(?<!/)$")
CLASSES = {
    "unknown",
    "grass_herbaceous",
    "shrub",
    "tree",
    "mixed",
    "non_vegetation",
}
ZONES = {"left", "right", "median", "special"}
DATA_STATUSES = {"real", "estimated", "prepared", "simulated", "inconclusive"}
PROVENANCE_STATUSES = {"validated", "prepared", "needs_validation"}
LICENSE_STATUSES = {"approved", "pending", "unknown", "not_applicable"}
CONSENT_STATUSES = {"approved", "pending", "unknown", "not_applicable"}
GATE_STATUSES = {"complete", "pending"}


class DatasetManifestError(ValueError):
    """Raised when a dataset manifest is incomplete or would open a closed gate."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DatasetManifestError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _load_manifest(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except OSError as exc:
        raise DatasetManifestError(f"cannot read dataset manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DatasetManifestError(f"invalid dataset manifest JSON: {exc.msg}") from exc
    if not isinstance(payload, Mapping):
        raise DatasetManifestError("dataset manifest root must be a JSON object")
    return payload


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DatasetManifestError(f"{name} must be a JSON object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    missing = expected - value.keys()
    unknown = value.keys() - expected
    if missing:
        raise DatasetManifestError(f"{name} is missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise DatasetManifestError(f"{name} has unknown keys: {', '.join(sorted(unknown))}")


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetManifestError(f"{name} must be a non-empty string")
    return value


def _expect(value: Any, expected: Any, name: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise DatasetManifestError(f"{name} must be {expected!r}")


def _date(value: Any, name: str) -> None:
    text = _nonempty_string(value, name)
    try:
        if date.fromisoformat(text).isoformat() != text:
            raise ValueError
    except ValueError as exc:
        raise DatasetManifestError(f"{name} must use YYYY-MM-DD") from exc


def _non_negative_int(value: Any, name: str) -> None:
    if type(value) is not int or value < 0:
        raise DatasetManifestError(f"{name} must be a non-negative integer")


def _validate_source(source: Mapping[str, Any], index: int) -> None:
    prefix = f"sources[{index}]"
    _exact_keys(
        source,
        {
            "source_id",
            "relative_path",
            "sha256",
            "data_status",
            "provenance_status",
            "license_status",
            "consent_status",
            "included_in_training",
            "exclusion_reason",
        },
        prefix,
    )
    _nonempty_string(source["source_id"], f"{prefix}.source_id")
    relative_path = _nonempty_string(source["relative_path"], f"{prefix}.relative_path")
    if SAFE_RELATIVE_PATH.fullmatch(relative_path) is None or ".." in Path(relative_path).parts:
        raise DatasetManifestError(f"{prefix}.relative_path must stay within the data root")
    sha256 = _nonempty_string(source["sha256"], f"{prefix}.sha256")
    if SHA256_PATTERN.fullmatch(sha256) is None:
        raise DatasetManifestError(f"{prefix}.sha256 must be a lowercase SHA-256 digest")
    for key, allowed in (
        ("data_status", DATA_STATUSES),
        ("provenance_status", PROVENANCE_STATUSES),
        ("license_status", LICENSE_STATUSES),
        ("consent_status", CONSENT_STATUSES),
    ):
        value = _nonempty_string(source[key], f"{prefix}.{key}")
        if value not in allowed:
            raise DatasetManifestError(f"{prefix}.{key} has unsupported value {value!r}")
    if type(source["included_in_training"]) is not bool:
        raise DatasetManifestError(f"{prefix}.included_in_training must be a boolean")
    if source["included_in_training"]:
        if source["data_status"] != "real":
            raise DatasetManifestError(
                f"{prefix}.included_in_training requires data_status=real"
            )
        if source["provenance_status"] != "validated":
            raise DatasetManifestError(
                f"{prefix}.included_in_training requires provenance_status=validated"
            )
        if source["license_status"] != "approved":
            raise DatasetManifestError(
                f"{prefix}.included_in_training requires license_status=approved"
            )
        if source["consent_status"] not in {"approved", "not_applicable"}:
            raise DatasetManifestError(
                f"{prefix}.included_in_training requires consent_status=approved"
            )
    if source["exclusion_reason"] is not None:
        _nonempty_string(source["exclusion_reason"], f"{prefix}.exclusion_reason")


def _validate_labels(labels: Mapping[str, Any]) -> tuple[int, bool]:
    _exact_keys(
        labels,
        {
            "status",
            "taxonomy_version",
            "annotator_count",
            "independent_annotation",
            "adjudication_status",
            "label_source_status",
            "counts_by_class",
            "counts_by_zone",
        },
        "labels",
    )
    status = _nonempty_string(labels["status"], "labels.status")
    if status not in {"not_started", "draft", "adjudicated"}:
        raise DatasetManifestError(f"labels.status has unsupported value {status!r}")
    _nonempty_string(labels["taxonomy_version"], "labels.taxonomy_version")
    _non_negative_int(labels["annotator_count"], "labels.annotator_count")
    if type(labels["independent_annotation"]) is not bool:
        raise DatasetManifestError("labels.independent_annotation must be a boolean")
    adjudication_status = _nonempty_string(
        labels["adjudication_status"], "labels.adjudication_status"
    )
    if adjudication_status not in {"not_started", "pending", "complete"}:
        raise DatasetManifestError(
            f"labels.adjudication_status has unsupported value {adjudication_status!r}"
        )
    label_source_status = _nonempty_string(
        labels["label_source_status"], "labels.label_source_status"
    )
    if label_source_status not in {"missing", "draft", "validated"}:
        raise DatasetManifestError(
            f"labels.label_source_status has unsupported value {label_source_status!r}"
        )

    counts_by_class = _object(labels["counts_by_class"], "labels.counts_by_class")
    _exact_keys(counts_by_class, CLASSES, "labels.counts_by_class")
    total = 0
    for cover_type, count in counts_by_class.items():
        _non_negative_int(count, f"labels.counts_by_class.{cover_type}")
        total += count

    counts_by_zone = _object(labels["counts_by_zone"], "labels.counts_by_zone")
    _exact_keys(counts_by_zone, ZONES, "labels.counts_by_zone")
    for zone, count in counts_by_zone.items():
        _non_negative_int(count, f"labels.counts_by_zone.{zone}")

    if status == "adjudicated" and (
        labels["annotator_count"] < 2
        or labels["independent_annotation"] is not True
        or adjudication_status != "complete"
        or label_source_status != "validated"
    ):
        raise DatasetManifestError(
            "labels.status=adjudicated requires independent annotation and adjudication"
        )
    if total and status == "not_started":
        raise DatasetManifestError(
            "labels with observations cannot remain labels.status=not_started"
        )
    return total, status == "adjudicated"


def _validate_splits(splits: Mapping[str, Any]) -> bool:
    _exact_keys(
        splits,
        {
            "strategy",
            "spatial_holdout_status",
            "temporal_holdout_status",
            "leakage_check_status",
            "spatial_holdout",
            "temporal_holdout",
        },
        "splits",
    )
    _expect(splits["strategy"], "spatial_and_temporal_holdout", "splits.strategy")
    for key, allowed in (
        ("spatial_holdout_status", {"pending", "complete"}),
        ("temporal_holdout_status", {"pending", "complete"}),
        ("leakage_check_status", {"not_run", "passed", "failed"}),
    ):
        value = _nonempty_string(splits[key], f"splits.{key}")
        if value not in allowed:
            raise DatasetManifestError(f"splits.{key} has unsupported value {value!r}")
    for key in ("spatial_holdout", "temporal_holdout"):
        value = splits[key]
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise DatasetManifestError(f"splits.{key} must be an array")
        for item in value:
            _nonempty_string(item, f"splits.{key}[]")
    return (
        splits["spatial_holdout_status"] == "complete"
        and splits["temporal_holdout_status"] == "complete"
        and splits["leakage_check_status"] == "passed"
        and bool(splits["spatial_holdout"])
        and bool(splits["temporal_holdout"])
    )


def _validate_gates(gates: Any) -> bool:
    if not isinstance(gates, list) or not gates:
        raise DatasetManifestError("gates must be a non-empty array")
    for index, gate_value in enumerate(gates):
        gate = _object(gate_value, f"gates[{index}]")
        _exact_keys(gate, {"id", "status", "evidence"}, f"gates[{index}]")
        _nonempty_string(gate["id"], f"gates[{index}].id")
        status = _nonempty_string(gate["status"], f"gates[{index}].status")
        if status not in GATE_STATUSES:
            raise DatasetManifestError(f"gates[{index}].status has unsupported value {status!r}")
        _nonempty_string(gate["evidence"], f"gates[{index}].evidence")
    return all(gate["status"] == "complete" for gate in gates)


def verify_dataset_manifest(manifest_path: Path) -> Mapping[str, Any]:
    payload = _load_manifest(manifest_path)
    _exact_keys(
        payload,
        {
            "schema_version",
            "dataset_id",
            "dataset_version",
            "created_at",
            "owner",
            "purpose",
            "taxonomy_version",
            "status",
            "source_review_id",
            "source_manifest",
            "sources",
            "labels",
            "splits",
            "exclusions",
            "eligibility",
            "gates",
        },
        "dataset",
    )
    _expect(payload["schema_version"], 1, "schema_version")
    for key in (
        "dataset_id",
        "dataset_version",
        "owner",
        "purpose",
        "taxonomy_version",
        "source_review_id",
        "source_manifest",
    ):
        _nonempty_string(payload[key], key)
    _date(payload["created_at"], "created_at")
    status = _nonempty_string(payload["status"], "status")
    if status not in {"blocked", "draft", "validated"}:
        raise DatasetManifestError(f"status has unsupported value {status!r}")

    sources = payload["sources"]
    if not isinstance(sources, list) or not sources:
        raise DatasetManifestError("sources must be a non-empty array")
    for index, source_value in enumerate(sources):
        _validate_source(_object(source_value, f"sources[{index}]"), index)

    label_count, labels_ready = _validate_labels(_object(payload["labels"], "labels"))
    splits_ready = _validate_splits(_object(payload["splits"], "splits"))

    exclusions = payload["exclusions"]
    if not isinstance(exclusions, list) or not exclusions:
        raise DatasetManifestError("exclusions must be a non-empty array")
    for index, exclusion in enumerate(exclusions):
        _nonempty_string(exclusion, f"exclusions[{index}]")

    eligibility = _object(payload["eligibility"], "eligibility")
    _exact_keys(
        eligibility,
        {
            "eligible_for_model_training",
            "eligible_for_official_reporting",
            "eligible_for_operations",
        },
        "eligibility",
    )
    for key in eligibility:
        if type(eligibility[key]) is not bool:
            raise DatasetManifestError(f"eligibility.{key} must be a boolean")
    if eligibility["eligible_for_operations"] or eligibility["eligible_for_official_reporting"]:
        raise DatasetManifestError(
            "this academic dataset gate cannot authorize operations or official reporting"
        )

    gates_complete = _validate_gates(payload["gates"])
    if eligibility["eligible_for_model_training"]:
        if status != "validated":
            raise DatasetManifestError(
                "model-training eligibility requires status=validated"
            )
        if not gates_complete or not labels_ready or label_count == 0 or not splits_ready:
            raise DatasetManifestError(
                "model-training eligibility requires complete labels, gates, and splits"
            )
        if not all(source["included_in_training"] for source in sources):
            raise DatasetManifestError(
                "model-training eligibility requires every listed source to be included"
            )
    elif status == "validated":
        raise DatasetManifestError(
            "status=validated requires eligible_for_model_training=true"
        )
    if gates_complete and not eligibility["eligible_for_model_training"]:
        raise DatasetManifestError(
            "all gates are complete but eligibility is closed; record the review explicitly"
        )
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = verify_dataset_manifest(args.manifest)
    except DatasetManifestError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"OK {args.manifest}: status={payload['status']} training_eligible=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
