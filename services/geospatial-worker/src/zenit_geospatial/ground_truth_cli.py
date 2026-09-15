"""GEO-002 ground truth tooling: sampling plan, eligibility manifest and pilot report.

Inputs are JSON files or ``-`` for stdin; results are JSON on stdout. Nothing here
authorizes field work or mowing, and non-real input is always reported as such.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from statistics import fmean
from typing import Any

from zenit_geospatial.ground_truth_agreement import (
    bland_altman,
    cluster_bootstrap,
    cohen_kappa,
    height_class,
    icc_2_1,
    krippendorff_alpha_nominal,
    threshold_agreement,
    weighted_kappa,
)
from zenit_geospatial.ground_truth_rules import (
    PROTOCOL_VERSION,
    AdjudicationPolicy,
    EligibilityPolicy,
    adjudication_triggers,
    summarize_eligibility,
)
from zenit_geospatial.ground_truth_sampling import plan_campaign

CALIBRATION_KAPPA = 0.6  # Academic assumption from protocol section 7.4, not an official target.
GROUP_KEYS = ("zone", "season", "road_code", "lighting")

Observation = Mapping[str, Any]


def _load(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _observations(document: Any) -> list[Observation]:
    items = document.get("observations") if isinstance(document, Mapping) else document
    if not isinstance(items, list) or not all(isinstance(item, Mapping) for item in items):
        raise ValueError("expected a list of observations or an object with 'observations'")
    return items


def _pair(observation: Observation) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    annotations = observation.get("annotations")
    if not isinstance(annotations, list) or len(annotations) != 2:
        raise ValueError(f"observation {observation.get('observation_id')} needs 2 annotations")
    return annotations[0], annotations[1]


def _readings(observation: Observation) -> list[float]:
    return [
        float(annotation["photo_height_cm"])
        for annotation in _pair(observation)
        if annotation.get("photo_height_cm") is not None
    ]


def _cover_kappa(items: Sequence[Observation]) -> float | None:
    return cohen_kappa([tuple(a.get("cover_class") for a in _pair(item)) for item in items])


def _photo_pairs(items: Sequence[Observation]) -> list[tuple[float, float]]:
    return [(values[0], values[1]) for item in items if len(values := _readings(item)) == 2]


def _photo_icc(items: Sequence[Observation]) -> float | None:
    pairs = _photo_pairs(items)
    return icc_2_1(pairs) if len(pairs) >= 2 else None


def _class_kappa(items: Sequence[Observation]) -> float | None:
    pairs = [(height_class(first), height_class(second)) for first, second in _photo_pairs(items)]
    return weighted_kappa(pairs, ["N1", "N2", "N3"])


def _field_pairs(items: Sequence[Observation]) -> list[tuple[float, float]]:
    return [
        (fmean(readings), float(item["field_height_cm"]))
        for item in items
        if item.get("field_height_cm") is not None and (readings := _readings(item))
    ]


def _field_icc(items: Sequence[Observation]) -> float | None:
    pairs = _field_pairs(items)
    return icc_2_1(pairs) if len(pairs) >= 2 else None


def _with_ci(
    items: Sequence[Observation],
    statistic: Callable[[Sequence[Observation]], float | None],
    arguments: argparse.Namespace,
) -> dict[str, Any]:
    interval = cluster_bootstrap(
        items,
        lambda item: item.get("cell_id") or item.get("observation_id"),
        statistic,
        resamples=arguments.resamples,
        seed=arguments.seed,
    )
    return {key: _round(value) for key, value in asdict(interval).items()}


def _round(value: Any) -> Any:
    return round(value, 4) if isinstance(value, float) else value


def build_report(items: Sequence[Observation], arguments: argparse.Namespace) -> dict[str, Any]:
    policy = AdjudicationPolicy()
    triggered = {}
    for item in items:
        triggers = adjudication_triggers(_pair(item), item.get("field_height_cm"), policy)
        if triggers:
            triggered[str(item.get("observation_id"))] = [str(trigger) for trigger in triggers]
    annotations = [annotation for item in items for annotation in _pair(item)]
    cover_kappa = _with_ci(items, _cover_kappa, arguments)
    photo_bland_altman = bland_altman(_photo_pairs(items))
    field_bland_altman = bland_altman(_field_pairs(items))
    statuses = Counter(str(item.get("data_status")) for item in items)
    non_real = set(statuses) != {"real"}
    confusion = Counter(
        f"{first.get('cover_class')} | {second.get('cover_class')}"
        for first, second in map(_pair, items)
    )

    by_group: dict[str, dict[str, Any]] = {}
    for key in GROUP_KEYS:
        values = sorted({str(item[key]) for item in items if item.get(key) is not None})
        if values:
            by_group[key] = {
                value: {
                    "observations": len(subset),
                    "cover_class_kappa": _round(_cover_kappa(subset)),
                    "photo_height_icc_2_1": _round(_photo_icc(subset)),
                }
                for value in values
                if (subset := [item for item in items if str(item.get(key)) == value])
            }

    return {
        "protocol_version": PROTOCOL_VERSION,
        "observations": len(items),
        "input_data_statuses": dict(sorted(statuses.items())),
        "non_real_input": non_real,
        "limitations": [
            "Governance eligibility is not checked here; run the eligibility command first.",
            "Non-real input is only a tooling exercise and never pilot evidence.",
            "Photo readings are quality control and never replace field height.",
        ],
        "cover_class": {
            "cohen_kappa": cover_kappa,
            "krippendorff_alpha_nominal": _round(
                krippendorff_alpha_nominal(
                    [[a.get("cover_class") for a in _pair(item)] for item in items]
                )
            ),
            "confusion_pairs": dict(sorted(confusion.items())),
            "unknown_rate": _round(
                sum(1 for a in annotations if a.get("cover_class") == "unknown") / len(annotations)
            ),
            "provisional_calibration_gate": {
                "kappa_threshold": CALIBRATION_KAPPA,
                "passed": None
                if non_real or cover_kappa["estimate"] is None
                else cover_kappa["estimate"] >= CALIBRATION_KAPPA,
                "evaluated_on_real_input": not non_real,
                "academic_assumption": True,
            },
        },
        "quality": {
            "cohen_kappa": _round(
                cohen_kappa([tuple(a.get("quality") for a in _pair(item)) for item in items])
            ),
            "rejected_rate": _round(
                sum(1 for a in annotations if a.get("quality") == "rejected") / len(annotations)
            ),
        },
        "photo_height": {
            "pairs": len(_photo_pairs(items)),
            "icc_2_1": _with_ci(items, _photo_icc, arguments),
            "height_class_weighted_kappa": _with_ci(items, _class_kappa, arguments),
            "bland_altman": _rounded_dict(photo_bland_altman),
            "threshold_agreement": {
                f"gt_{int(threshold)}_cm": _round(share)
                for threshold, share in threshold_agreement(_photo_pairs(items)).items()
            },
        },
        "field_vs_photo_height": {
            "pairs": len(_field_pairs(items)),
            "icc_2_1": _with_ci(items, _field_icc, arguments),
            "bland_altman_photo_minus_field": _rounded_dict(field_bland_altman),
        },
        "adjudication": {
            "required": len(triggered),
            "rate": _round(len(triggered) / len(items)) if items else None,
            "by_trigger": dict(
                sorted(Counter(t for triggers in triggered.values() for t in triggers).items())
            ),
            "observations": triggered,
        },
        "by_group": by_group,
        "bootstrap": {"seed": arguments.seed, "resamples": arguments.resamples, "cluster": "cell"},
    }


def _rounded_dict(value: Any) -> dict[str, Any] | None:
    return None if value is None else {key: _round(item) for key, item in asdict(value).items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zenit-ground-truth",
        description="GEO-002 ground truth tooling. Outputs never authorize field work or mowing.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan", help="seeded sampling plan from metric zone polygons")
    plan.add_argument("--zones", required=True, help="GeoJSON FeatureCollection path or -")
    plan.add_argument("--seed", type=int, required=True)
    plan.add_argument("--campaign-id", required=True)
    plan.add_argument("--points-per-cell", type=int, default=3)
    plan.add_argument("--substitutes", type=int, default=3)
    plan.add_argument("--edge-setback-m", type=float, default=0.0)

    eligibility = commands.add_parser("eligibility", help="inclusion/exclusion manifest summary")
    eligibility.add_argument("--observations", required=True, help="JSON path or -")
    eligibility.add_argument("--approved-campaign", action="append", default=[])
    eligibility.add_argument("--approved-protocol", action="append", default=[])
    eligibility.add_argument("--registered-device", action="append", default=[])

    report = commands.add_parser("report", help="agreement and adjudication report")
    report.add_argument("--annotations", required=True, help="JSON path or -")
    report.add_argument("--seed", type=int, default=0)
    report.add_argument("--resamples", type=int, default=1000)
    return parser


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    if arguments.command == "plan":
        document = _load(arguments.zones)
        return plan_campaign(
            document.get("features", []),
            seed=arguments.seed,
            campaign_id=arguments.campaign_id,
            points_per_cell=arguments.points_per_cell,
            substitutes=arguments.substitutes,
            edge_setback_m=arguments.edge_setback_m,
        )
    if arguments.command == "eligibility":
        policy = EligibilityPolicy(
            approved_campaigns=frozenset(arguments.approved_campaign),
            approved_protocols=frozenset(arguments.approved_protocol),
            registered_devices=frozenset(arguments.registered_device),
        )
        return summarize_eligibility(_observations(_load(arguments.observations)), policy)
    items = _observations(_load(arguments.annotations))
    if not items:
        raise ValueError("report needs at least one observation")
    return build_report(items, arguments)


def main(argv: Sequence[str] | None = None) -> None:
    arguments = build_parser().parse_args(argv)
    try:
        result = run(arguments)
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"zenit-ground-truth: {error}") from None
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
