from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "zenit-simulated-mowing-timeseries-v1"
DATASET_ID = "zenit-simulated-mowing-timeseries"
ZONE_TYPES = ("left", "right", "median", "special")
_RECORD_NAMESPACE = uuid.UUID("8376b859-1cc5-445e-a0e4-f6c68d86986d")
_FIELDNAMES = (
    "record_id",
    "scenario_date",
    "road_code",
    "segment_index",
    "segment_length_m",
    "zone_type",
    "threshold_cm",
    "cover_type",
    "simulated_rainfall_mm",
    "simulated_growth_cm",
    "simulated_height_before_mowing_cm",
    "simulated_mowing_event",
    "simulated_height_after_mowing_cm",
    "days_since_simulated_mowing",
    "data_status",
    "source_type",
    "eligible_for_model_training",
    "eligible_for_official_reporting",
    "eligible_for_operations",
    "authorizes_mowing",
)
_LIMITATIONS = (
    "All values are algorithmically generated and are not field or satellite observations.",
    "Mowing events are scripted scenario inputs, not recommendations or evidence of execution.",
    "The dataset may rehearse ingestion and visualization but cannot train or validate AI-001.",
)


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    start_date: date = date(2026, 8, 1)
    days: int = 30
    road_code: str = "SP021"
    segment_index: int = 195
    segment_length_m: int = 100
    seed: int = 20260915

    def __post_init__(self) -> None:
        if not 2 <= self.days <= 366:
            raise ValueError("days must be between 2 and 366")
        if not self.road_code.strip():
            raise ValueError("road_code must not be empty")
        if self.segment_index < 0:
            raise ValueError("segment_index must be non-negative")
        if self.segment_length_m != 100:
            raise ValueError("ZENIT scenarios must use 100 m segments")


def _zone_seed(seed: int, zone_type: str) -> int:
    digest = hashlib.sha256(f"{seed}:{zone_type}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _mowing_days(zone_type: str, days: int) -> frozenset[int]:
    schedule = {
        "left": (12,),
        "right": (16,),
        "median": (20,),
        "special": (8, 18, 28),
    }
    return frozenset(day for day in schedule[zone_type] if day < days)


def build_records(config: ScenarioConfig | None = None) -> list[dict[str, Any]]:
    config = config or ScenarioConfig()
    records: list[dict[str, Any]] = []
    initial_height = {"left": 18.0, "right": 21.0, "median": 16.0, "special": 7.0}
    base_growth = {"left": 0.65, "right": 0.72, "median": 0.58, "special": 0.48}
    post_mowing_height = {"left": 8.0, "right": 8.0, "median": 8.0, "special": 5.0}

    for zone_type in ZONE_TYPES:
        rng = random.Random(_zone_seed(config.seed, zone_type))
        height_cm = initial_height[zone_type]
        last_mowing_day: int | None = None
        mowing_days = _mowing_days(zone_type, config.days)
        for day_index in range(config.days):
            scenario_date = config.start_date + timedelta(days=day_index)
            rainfall_mm = round(max(0.0, rng.gauss(4.2, 4.8)), 1)
            growth_cm = round(
                max(0.05, base_growth[zone_type] + rainfall_mm * 0.025 + rng.uniform(-0.16, 0.16)),
                2,
            )
            height_before_mowing_cm = round(height_cm + growth_cm, 2)
            mowing_event = day_index in mowing_days
            height_after_mowing_cm = (
                post_mowing_height[zone_type] if mowing_event else height_before_mowing_cm
            )
            if mowing_event:
                last_mowing_day = day_index
            days_since_mowing = (
                None if last_mowing_day is None else day_index - last_mowing_day
            )
            record_key = (
                f"{config.seed}:{config.road_code}:{config.segment_index}:"
                f"{zone_type}:{scenario_date.isoformat()}"
            )
            records.append(
                {
                    "record_id": str(uuid.uuid5(_RECORD_NAMESPACE, record_key)),
                    "scenario_date": scenario_date.isoformat(),
                    "road_code": config.road_code,
                    "segment_index": config.segment_index,
                    "segment_length_m": config.segment_length_m,
                    "zone_type": zone_type,
                    "threshold_cm": 10 if zone_type == "special" else 30,
                    "cover_type": "grass_herbaceous",
                    "simulated_rainfall_mm": rainfall_mm,
                    "simulated_growth_cm": growth_cm,
                    "simulated_height_before_mowing_cm": height_before_mowing_cm,
                    "simulated_mowing_event": mowing_event,
                    "simulated_height_after_mowing_cm": round(height_after_mowing_cm, 2),
                    "days_since_simulated_mowing": days_since_mowing,
                    "data_status": "simulated",
                    "source_type": "algorithmically_generated_scenario",
                    "eligible_for_model_training": False,
                    "eligible_for_official_reporting": False,
                    "eligible_for_operations": False,
                    "authorizes_mowing": False,
                }
            )
            height_cm = height_after_mowing_cm
    return records


def render_csv(records: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=_FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(record)
    return output.getvalue()


def build_manifest(
    config: ScenarioConfig, records: list[dict[str, Any]], csv_text: str
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "dataset_version": "v0.1-presentation-only",
        "purpose": "pipeline_rehearsal_and_presentation",
        "data_status": "simulated",
        "source_type": "algorithmically_generated_scenario",
        "scenario": {
            "seed": config.seed,
            "road_code": config.road_code,
            "segment_index": config.segment_index,
            "segment_length_m": config.segment_length_m,
            "start_date": config.start_date.isoformat(),
            "end_date": (config.start_date + timedelta(days=config.days - 1)).isoformat(),
            "days": config.days,
            "zone_types": list(ZONE_TYPES),
            "record_count": len(records),
        },
        "checksums": {"csv_sha256": hashlib.sha256(csv_text.encode()).hexdigest()},
        "eligibility": {
            "eligible_for_model_training": False,
            "eligible_for_official_reporting": False,
            "eligible_for_operations": False,
            "authorizes_mowing": False,
        },
        "limitations": list(_LIMITATIONS),
    }


def validate(records: list[dict[str, Any]], manifest: dict[str, Any], csv_text: str) -> None:
    if not records:
        raise ValueError("simulated dataset must contain records")
    scenario = manifest.get("scenario")
    eligibility = manifest.get("eligibility")
    if not isinstance(scenario, dict) or scenario.get("record_count") != len(records):
        raise ValueError("manifest record_count does not match the CSV")
    if manifest.get("data_status") != "simulated" or not isinstance(eligibility, dict):
        raise ValueError("manifest must be explicitly simulated")
    for field, value in eligibility.items():
        is_safety_flag = field.startswith("eligible_for_") or field == "authorizes_mowing"
        if is_safety_flag and value is not False:
            raise ValueError(f"manifest {field} must remain false")
    if manifest.get("checksums", {}).get("csv_sha256") != hashlib.sha256(
        csv_text.encode()
    ).hexdigest():
        raise ValueError("manifest CSV checksum does not match")

    seen_cells: set[tuple[str, int, str, str]] = set()
    for record in records:
        if record.get("data_status") != "simulated":
            raise ValueError("every record must be simulated")
        if record.get("segment_length_m") != 100:
            raise ValueError("every record must preserve the 100 m segment rule")
        if record.get("zone_type") not in ZONE_TYPES:
            raise ValueError("unsupported zone_type")
        expected_threshold = 10 if record["zone_type"] == "special" else 30
        if record.get("threshold_cm") != expected_threshold:
            raise ValueError("record has an invalid zone threshold")
        for field in (
            "eligible_for_model_training",
            "eligible_for_official_reporting",
            "eligible_for_operations",
            "authorizes_mowing",
        ):
            if record.get(field) is not False:
                raise ValueError(f"record {field} must remain false")
        cell = (
            str(record["road_code"]),
            int(record["segment_index"]),
            str(record["zone_type"]),
            str(record["scenario_date"]),
        )
        if cell in seen_cells:
            raise ValueError("duplicate road/segment/zone/date record")
        seen_cells.add(cell)


def write_dataset(
    config: ScenarioConfig, output_directory: Path, repository_root: Path
) -> tuple[Path, Path]:
    output_directory = output_directory.resolve()
    raw_directory = (repository_root / "data" / "raw").resolve()
    if output_directory == raw_directory or output_directory.is_relative_to(raw_directory):
        raise ValueError("simulated outputs must never be written under data/raw")
    records = build_records(config)
    csv_text = render_csv(records)
    manifest = build_manifest(config, records, csv_text)
    validate(records, manifest, csv_text)
    output_directory.mkdir(parents=True, exist_ok=True)
    csv_path = output_directory / "mowing-timeseries.csv"
    manifest_path = output_directory / "mowing-timeseries.manifest.json"
    csv_path.write_text(csv_text, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return csv_path, manifest_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate presentation-only simulated mowing time-series data"
    )
    parser.add_argument("--output-directory", type=Path, default=Path("data/simulated/sp021-195"))
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 8, 1))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--road-code", default="SP021")
    parser.add_argument("--segment-index", type=int, default=195)
    parser.add_argument("--seed", type=int, default=20260915)
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    config = ScenarioConfig(
        start_date=arguments.start_date,
        days=arguments.days,
        road_code=arguments.road_code,
        segment_index=arguments.segment_index,
        seed=arguments.seed,
    )
    try:
        csv_path, manifest_path = write_dataset(config, arguments.output_directory, Path.cwd())
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(
        f"csv={csv_path} manifest={manifest_path} data_status=simulated "
        "training_eligible=false operationally_eligible=false"
    )


if __name__ == "__main__":
    main()
