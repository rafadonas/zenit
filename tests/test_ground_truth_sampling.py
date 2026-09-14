import math

import pytest

from zenit_geospatial.ground_truth_sampling import plan_campaign


def zone_feature(segment_index=0, zone="left", rings=None, **properties):
    if rings is None:
        rings = [[[0, 0], [100, 0], [100, 10], [0, 10], [0, 0]]]
    return {
        "type": "Feature",
        "properties": {
            "road_code": "SP021",
            "segment_index": segment_index,
            "zone": zone,
            "data_status": "real",
            **properties,
        },
        "geometry": {"type": "Polygon", "coordinates": rings},
    }


def points(plan, cell=0):
    return [(point["x"], point["y"]) for point in plan["cells"][cell]["points"]]


def test_plan_draws_primary_and_substitute_points_inside_zone_with_setback() -> None:
    plan = plan_campaign([zone_feature()], seed=42, campaign_id="c1", edge_setback_m=2)

    cell = plan["cells"][0]
    assert [point["role"] for point in cell["points"]] == ["primary"] * 3 + ["substitute"] * 3
    assert all(2 <= x <= 98 and 2 <= y <= 8 for x, y in points(plan))
    assert cell["shortfall"] is None
    assert cell["eligible_for_field_use"] is True
    assert plan["authorizes_field_work"] is False
    assert plan["summary"] == {
        "cells": 1,
        "primary_points": 3,
        "substitute_points": 3,
        "cells_with_shortfall": 0,
        "cells_not_eligible_for_field_use": 0,
    }


def test_same_seed_reproduces_plan_and_different_seed_changes_it() -> None:
    first = plan_campaign([zone_feature()], seed=1, campaign_id="c1")
    second = plan_campaign([zone_feature()], seed=1, campaign_id="c1")
    other = plan_campaign([zone_feature()], seed=2, campaign_id="c1")

    assert first == second
    assert points(first) != points(other)


def test_adding_cells_does_not_move_existing_points() -> None:
    alone = plan_campaign([zone_feature(segment_index=5)], seed=9, campaign_id="c1")
    together = plan_campaign(
        [zone_feature(segment_index=4), zone_feature(segment_index=5)], seed=9, campaign_id="c1"
    )

    assert points(alone) == points(together, cell=1)


def test_planned_points_are_stable_across_campaigns() -> None:
    wet = plan_campaign([zone_feature()], seed=3, campaign_id="wet")
    dry = plan_campaign([zone_feature()], seed=3, campaign_id="dry")

    assert wet["cells"] == dry["cells"]
    assert wet["campaign_id"] != dry["campaign_id"]


def test_points_avoid_polygon_holes() -> None:
    rings = [
        [[0, 0], [20, 0], [20, 20], [0, 20], [0, 0]],
        [[5, 5], [15, 5], [15, 15], [5, 15], [5, 5]],
    ]

    plan = plan_campaign([zone_feature(rings=rings)], seed=11, campaign_id="c1", substitutes=20)

    assert len(points(plan)) == 23
    assert not any(5 < x < 15 and 5 < y < 15 for x, y in points(plan))


def test_setback_distance_to_every_edge_is_respected() -> None:
    triangle = [[[0, 0], [30, 0], [0, 30], [0, 0]]]

    plan = plan_campaign([zone_feature(rings=triangle)], seed=5, campaign_id="c1", edge_setback_m=3)

    for x, y in points(plan):
        assert x >= 3 and y >= 3
        assert (30 - x - y) / math.sqrt(2) >= 3 - 1e-3


def test_narrow_zone_reports_shortfall_instead_of_convenience_points() -> None:
    plan = plan_campaign(
        [zone_feature()], seed=1, campaign_id="c1", edge_setback_m=6, max_attempts=200
    )

    assert plan["cells"][0]["points"] == []
    assert plan["cells"][0]["shortfall"] == "insufficient_area_after_setback"
    assert plan["summary"]["cells_with_shortfall"] == 1


def test_non_real_geometry_is_not_eligible_for_field_use() -> None:
    plan = plan_campaign(
        [zone_feature(zone="special", data_status="prepared", historical_class="N2")],
        seed=1,
        campaign_id="c1",
    )

    cell = plan["cells"][0]
    assert cell["eligible_for_field_use"] is False
    assert cell["threshold_cm"] == 10
    assert cell["strata"] == {"historical_class": "N2"}
    assert plan["summary"]["cells_not_eligible_for_field_use"] == 1


@pytest.mark.parametrize(
    ("feature", "message"),
    [
        (zone_feature(zone="shoulder"), "zone must be"),
        (zone_feature(segment_index=-1), "segment_index"),
        (zone_feature(rings=[[[0, 0], [1, 0], [0, 0]]]), "closed"),
        ({**zone_feature(), "geometry": {"type": "Point", "coordinates": [0, 0]}}, "Polygon"),
    ],
)
def test_invalid_zone_features_are_rejected(feature, message) -> None:
    with pytest.raises(ValueError, match=message):
        plan_campaign([feature], seed=1, campaign_id="c1")


def test_duplicate_cells_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        plan_campaign([zone_feature(), zone_feature()], seed=1, campaign_id="c1")
