from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import uuid
from collections import defaultdict
from datetime import date
from itertools import pairwise
from pathlib import Path
from typing import Any

FEATURE_DEFINITION_VERSION = "zenit-simulated-feature-snapshot-v1"
DATASET_ID = "zenit-simulated-feature-snapshots"
ZONE_TYPES = ("left", "right", "median", "special")
WARMUP_DAYS = 14
_SNAPSHOT_NAMESPACE = uuid.UUID("e26ee40d-47e1-498e-b159-974e9657b915")
_ZONE_NAMESPACE = uuid.UUID("325055d5-70e8-4ea1-a696-343037217dd3")
_FIELDNAMES = (
    "feature_snapshot_id",
    "segment_zone_id",
    "as_of_date",
    "road_code",
    "segment_index",
    "segment_length_m",
    "zone_type",
    "applicable_threshold_cm",
    "simulated_current_height_cm",
    "simulated_height_lag_1d_cm",
    "simulated_height_lag_7d_cm",
    "simulated_height_lag_14d_cm",
    "simulated_growth_rolling_7d_cm",
    "simulated_rainfall_rolling_7d_mm",
    "simulated_rainfall_rolling_14d_mm",
    "days_since_simulated_mowing",
    "simulated_historical_class",
    "simulated_threshold_state",
    "rehearsal_split_role",
    "source_record_ids",
    "input_window_sha256",
    "feature_definition_version",
    "data_status",
    "eligible_for_model_training",
    "eligible_for_official_reporting",
    "eligible_for_operations",
    "authorizes_mowing",
)
_FALSE_TEXT = {"false", "0", "no"}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_simulated_source(manifest: dict[str, Any]) -> None:
    if manifest.get("data_status") != "simulated":
        raise ValueError("source manifest must be explicitly simulated")
    eligibility = manifest.get("eligibility")
    if not isinstance(eligibility, dict):
        raise ValueError("source manifest must include eligibility flags")
    for field in (
        "eligible_for_model_training",
        "eligible_for_official_reporting",
        "eligible_for_operations",
        "authorizes_mowing",
    ):
        if eligibility.get(field) is not False:
            raise ValueError(f"source manifest {field} must remain false")


def load_source(csv_path: Path, manifest_path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    csv_bytes = csv_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _require_simulated_source(manifest)
    expected_checksum = manifest.get("checksums", {}).get("csv_sha256")
    if expected_checksum != _sha256(csv_bytes):
        raise ValueError("source CSV checksum does not match its manifest")
    records = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"))))
    if not records:
        raise ValueError("source CSV must contain records")
    for record in records:
        if record.get("data_status") != "simulated":
            raise ValueError("every source record must be simulated")
        for field in (
            "eligible_for_model_training",
            "eligible_for_official_reporting",
            "eligible_for_operations",
            "authorizes_mowing",
        ):
            if record.get(field, "").strip().lower() not in _FALSE_TEXT:
                raise ValueError(f"source record {field} must remain false")
    return records, manifest


def _historical_class(height_cm: float) -> str:
    if height_cm < 10:
        return "N1"
    if height_cm <= 30:
        return "N2"
    return "N3"


def _split_role(snapshot_index: int, snapshot_dates: int) -> str:
    development_end = int(snapshot_dates * 0.70)
    validation_end = int(snapshot_dates * 0.85)
    if snapshot_index < development_end:
        return "development_rehearsal"
    if snapshot_index < validation_end:
        return "validation_rehearsal"
    return "holdout_rehearsal"


def build_feature_snapshots(records: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_zone: dict[tuple[str, int, str], list[dict[str, str]]] = defaultdict(list)
    for record in records:
        zone = record["zone_type"]
        if zone not in ZONE_TYPES:
            raise ValueError("unsupported source zone_type")
        if int(record["segment_length_m"]) != 100:
            raise ValueError("source records must preserve the 100 m segment rule")
        expected_threshold = 10 if zone == "special" else 30
        if int(record["threshold_cm"]) != expected_threshold:
            raise ValueError("source record has an invalid zone threshold")
        key = (record["road_code"], int(record["segment_index"]), zone)
        by_zone[key].append(record)

    snapshots: list[dict[str, Any]] = []
    for (road_code, segment_index, zone), zone_records in sorted(by_zone.items()):
        zone_records.sort(key=lambda record: record["scenario_date"])
        dates = [date.fromisoformat(record["scenario_date"]) for record in zone_records]
        if len(set(dates)) != len(dates):
            raise ValueError("duplicate source date for a segment zone")
        if any((current - previous).days != 1 for previous, current in pairwise(dates)):
            raise ValueError("source records must form a contiguous daily series")
        snapshot_dates = len(zone_records) - WARMUP_DAYS
        if snapshot_dates <= 0:
            raise ValueError("source series must contain more than 14 days")
        zone_key = f"{road_code}:{segment_index}:{zone}"
        segment_zone_id = str(uuid.uuid5(_ZONE_NAMESPACE, zone_key))
        threshold = 10 if zone == "special" else 30
        for index in range(WARMUP_DAYS, len(zone_records)):
            current = zone_records[index]
            input_window = zone_records[index - 14 : index + 1]
            window_14d = zone_records[index - 13 : index + 1]
            window_7d = zone_records[index - 6 : index + 1]
            source_ids = [record["record_id"] for record in input_window]
            input_window_hash = _sha256(
                json.dumps(input_window, sort_keys=True, separators=(",", ":")).encode()
            )
            height = float(current["simulated_height_after_mowing_cm"])
            snapshot_key = f"{FEATURE_DEFINITION_VERSION}:{zone_key}:{current['scenario_date']}"
            snapshots.append(
                {
                    "feature_snapshot_id": str(uuid.uuid5(_SNAPSHOT_NAMESPACE, snapshot_key)),
                    "segment_zone_id": segment_zone_id,
                    "as_of_date": current["scenario_date"],
                    "road_code": road_code,
                    "segment_index": segment_index,
                    "segment_length_m": 100,
                    "zone_type": zone,
                    "applicable_threshold_cm": threshold,
                    "simulated_current_height_cm": round(height, 2),
                    "simulated_height_lag_1d_cm": round(
                        float(zone_records[index - 1]["simulated_height_after_mowing_cm"]), 2
                    ),
                    "simulated_height_lag_7d_cm": round(
                        float(zone_records[index - 7]["simulated_height_after_mowing_cm"]), 2
                    ),
                    "simulated_height_lag_14d_cm": round(
                        float(zone_records[index - 14]["simulated_height_after_mowing_cm"]), 2
                    ),
                    "simulated_growth_rolling_7d_cm": round(
                        sum(float(record["simulated_growth_cm"]) for record in window_7d), 2
                    ),
                    "simulated_rainfall_rolling_7d_mm": round(
                        sum(float(record["simulated_rainfall_mm"]) for record in window_7d), 1
                    ),
                    "simulated_rainfall_rolling_14d_mm": round(
                        sum(float(record["simulated_rainfall_mm"]) for record in window_14d), 1
                    ),
                    "days_since_simulated_mowing": current["days_since_simulated_mowing"],
                    "simulated_historical_class": _historical_class(height),
                    "simulated_threshold_state": "exceeds" if height > threshold else "within",
                    "rehearsal_split_role": _split_role(index - WARMUP_DAYS, snapshot_dates),
                    "source_record_ids": "|".join(source_ids),
                    "input_window_sha256": input_window_hash,
                    "feature_definition_version": FEATURE_DEFINITION_VERSION,
                    "data_status": "simulated",
                    "eligible_for_model_training": False,
                    "eligible_for_official_reporting": False,
                    "eligible_for_operations": False,
                    "authorizes_mowing": False,
                }
            )
    return sorted(snapshots, key=lambda row: (row["as_of_date"], row["zone_type"]))


def render_csv(snapshots: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=_FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(snapshots)
    return output.getvalue()


def build_manifest(
    snapshots: list[dict[str, Any]], output_csv: str, source_manifest: dict[str, Any]
) -> dict[str, Any]:
    roles: dict[str, int] = defaultdict(int)
    for snapshot in snapshots:
        roles[str(snapshot["rehearsal_split_role"])] += 1
    return {
        "schema_version": "zenit-simulated-feature-snapshot-manifest-v1",
        "dataset_id": DATASET_ID,
        "dataset_version": "v0.1-presentation-only",
        "feature_definition_version": FEATURE_DEFINITION_VERSION,
        "purpose": "feature_pipeline_and_temporal_split_rehearsal",
        "data_status": "simulated",
        "source_dataset": {
            "dataset_id": source_manifest["dataset_id"],
            "dataset_version": source_manifest["dataset_version"],
            "csv_sha256": source_manifest["checksums"]["csv_sha256"],
        },
        "snapshot_count": len(snapshots),
        "start_as_of": min(row["as_of_date"] for row in snapshots),
        "end_as_of": max(row["as_of_date"] for row in snapshots),
        "warmup_days": WARMUP_DAYS,
        "rehearsal_split_counts": dict(sorted(roles.items())),
        "checksums": {"csv_sha256": _sha256(output_csv.encode())},
        "eligibility": {
            "eligible_for_model_training": False,
            "eligible_for_official_reporting": False,
            "eligible_for_operations": False,
            "authorizes_mowing": False,
            "model_fitted": False,
        },
        "limitations": [
            "All features derive only from algorithmically generated simulated values.",
            "Split labels rehearse chronology and are not approved training partitions.",
            "A single simulated segment cannot provide a spatial holdout.",
            "No model was fitted, validated, calibrated, or promoted from this artifact.",
        ],
    }


def validate_output(
    snapshots: list[dict[str, Any]], manifest: dict[str, Any], csv_text: str
) -> None:
    if not snapshots:
        raise ValueError("feature snapshot dataset must not be empty")
    if manifest.get("data_status") != "simulated":
        raise ValueError("feature snapshot manifest must be simulated")
    if manifest.get("checksums", {}).get("csv_sha256") != _sha256(csv_text.encode()):
        raise ValueError("feature snapshot CSV checksum does not match")
    if manifest.get("snapshot_count") != len(snapshots):
        raise ValueError("feature snapshot count does not match")
    for field, value in manifest.get("eligibility", {}).items():
        if value is not False:
            raise ValueError(f"feature snapshot manifest {field} must remain false")
    for snapshot in snapshots:
        if snapshot["data_status"] != "simulated":
            raise ValueError("every feature snapshot must be simulated")
        for field in (
            "eligible_for_model_training",
            "eligible_for_official_reporting",
            "eligible_for_operations",
            "authorizes_mowing",
        ):
            if snapshot[field] is not False:
                raise ValueError(f"feature snapshot {field} must remain false")


def write_feature_snapshots(
    source_csv: Path, source_manifest_path: Path, output_directory: Path, repository_root: Path
) -> tuple[Path, Path]:
    output_directory = output_directory.resolve()
    raw_directory = (repository_root / "data" / "raw").resolve()
    if output_directory == raw_directory or output_directory.is_relative_to(raw_directory):
        raise ValueError("simulated outputs must never be written under data/raw")
    records, source_manifest = load_source(source_csv, source_manifest_path)
    snapshots = build_feature_snapshots(records)
    csv_text = render_csv(snapshots)
    manifest = build_manifest(snapshots, csv_text, source_manifest)
    validate_output(snapshots, manifest, csv_text)
    output_directory.mkdir(parents=True, exist_ok=True)
    csv_path = output_directory / "feature-snapshots.csv"
    manifest_path = output_directory / "feature-snapshots.manifest.json"
    csv_path.write_text(csv_text, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return csv_path, manifest_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build presentation-only simulated features")
    parser.add_argument(
        "--source-csv", type=Path, default=Path("data/simulated/sp021-195/mowing-timeseries.csv")
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=Path("data/simulated/sp021-195/mowing-timeseries.manifest.json"),
    )
    parser.add_argument("--output-directory", type=Path, default=Path("data/simulated/sp021-195"))
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    try:
        csv_path, manifest_path = write_feature_snapshots(
            arguments.source_csv, arguments.source_manifest, arguments.output_directory, Path.cwd()
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    print(
        f"csv={csv_path} manifest={manifest_path} data_status=simulated "
        "training_eligible=false model_fitted=false"
    )


if __name__ == "__main__":
    main()
