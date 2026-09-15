import io
import json
from pathlib import Path

import pytest

from zenit_geospatial.ground_truth_cli import build_parser, build_report, main, run

FIXTURES = Path(__file__).parent / "fixtures" / "ground_truth"
ZONES = str(FIXTURES / "zones_simulated.geojson")
OBSERVATIONS = str(FIXTURES / "observations_simulated.json")


def invoke(capsys, *argv: str) -> dict:
    main(list(argv))
    return json.loads(capsys.readouterr().out)


def real_observation(index: int, first: str, second: str, heights=(20, 21)) -> dict:
    return {
        "observation_id": f"obs-{index}",
        "cell_id": f"cell-{index % 3}",
        "zone": "left" if index % 2 else "right",
        "data_status": "real",
        "field_height_cm": heights[0],
        "annotations": [
            {"cover_class": first, "quality": "ok", "photo_height_cm": heights[0]},
            {"cover_class": second, "quality": "ok", "photo_height_cm": heights[1]},
        ],
    }


def test_plan_command_samples_every_simulated_cell_without_field_eligibility(capsys) -> None:
    plan = invoke(capsys, "plan", "--zones", ZONES, "--seed", "7", "--campaign-id", "sim")

    assert plan["summary"]["cells"] == 8
    assert plan["summary"]["primary_points"] == 24
    assert plan["summary"]["cells_not_eligible_for_field_use"] == 8
    assert plan["authorizes_field_work"] is False
    assert plan["authorizes_mowing"] is False
    assert plan["eligible_for_model_training"] is False


def test_eligibility_command_excludes_all_simulated_and_prepared_fixtures(capsys) -> None:
    summary = invoke(
        capsys,
        "eligibility",
        "--observations",
        OBSERVATIONS,
        "--approved-campaign",
        "sim-rehearsal",
        "--approved-protocol",
        "zenit-ground-truth-v0.1-draft",
        "--registered-device",
        "sim-device",
    )

    assert summary["candidates"] == 24
    assert summary["included"] == 0
    assert summary["excluded_by_reason"]["data_status_not_real"] == 24
    assert summary["data_statuses_seen"] == {"prepared": 4, "simulated": 20}


def test_report_command_reads_stdin_and_never_passes_gate_on_non_real_input(
    capsys, monkeypatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(Path(OBSERVATIONS).read_text()))

    report = invoke(capsys, "report", "--annotations", "-", "--resamples", "50")

    assert report["observations"] == 24
    assert report["non_real_input"] is True
    assert report["eligible_for_model_training"] is False
    assert report["eligible_for_official_reporting"] is False
    assert report["eligible_for_operations"] is False
    assert report["authorizes_field_work"] is False
    assert report["authorizes_mowing"] is False
    gate = report["cover_class"]["provisional_calibration_gate"]
    assert gate["passed"] is None
    assert gate["evaluated_on_real_input"] is False
    assert report["cover_class"]["cohen_kappa"]["resamples"] == 50
    assert report["adjudication"]["required"] == len(report["adjudication"]["observations"])
    assert set(report["by_group"]) == {"zone", "season", "road_code", "lighting"}


def test_report_on_real_input_evaluates_gate_and_adjudication() -> None:
    items = [real_observation(index, "tree", "tree") for index in range(6)]
    items += [real_observation(6, "shrub", "shrub"), real_observation(7, "shrub", "tree", (29, 31))]
    arguments = build_parser().parse_args(["report", "--annotations", "-", "--resamples", "20"])

    report = build_report(items, arguments)

    gate = report["cover_class"]["provisional_calibration_gate"]
    assert report["non_real_input"] is False
    assert gate["evaluated_on_real_input"] is True
    assert gate["passed"] is (report["cover_class"]["cohen_kappa"]["estimate"] >= 0.6)
    assert report["adjudication"]["observations"] == {
        "obs-7": [
            "cover_class_mismatch",
            "photo_height_threshold_crossing",
            "field_photo_threshold_crossing",
        ]
    }
    assert report["photo_height"]["threshold_agreement"] == {"gt_10_cm": 1.0, "gt_30_cm": 0.875}


def test_report_requires_exactly_two_annotations() -> None:
    arguments = build_parser().parse_args(["report", "--annotations", "-"])
    item = real_observation(1, "tree", "tree")
    item["annotations"] = item["annotations"][:1]

    with pytest.raises(ValueError, match="2 annotations"):
        build_report([item], arguments)


def test_invalid_input_exits_with_message(tmp_path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"observations": "nope"}))

    with pytest.raises(SystemExit, match="zenit-ground-truth: expected a list"):
        main(["report", "--annotations", str(broken)])


def test_missing_input_file_raises() -> None:
    arguments = build_parser().parse_args(["report", "--annotations", "-"])
    arguments.annotations = str(FIXTURES / "missing.json")

    with pytest.raises(OSError):
        run(arguments)
