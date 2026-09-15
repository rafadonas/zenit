"""Seeded, reproducible point sampling per road/segment/zone cell (GEO-002 section 4).

Zones are GeoJSON Polygon features in a metric CRS (default EPSG:31983, as stored in
``segment_zone.metric_geometry``). Each cell draws from its own seeded generator, so
adding cells never moves existing points and planned points stay stable across
campaigns. A plan is not an observation and never authorizes field work.
"""

from __future__ import annotations

import math
import random
import uuid
from collections.abc import Iterable, Mapping, Sequence
from itertools import pairwise
from typing import Any

from zenit_geospatial.ground_truth_rules import PROTOCOL_VERSION

SAMPLER_VERSION = "gt-sampler-v1"
ZONES = ("left", "right", "median", "special")
_POINT_NAMESPACE = uuid.UUID("5f0d7a52-3c1e-4d7b-9b8e-0a6f1d2c9e41")

Point = tuple[float, float]
Ring = Sequence[Point]
CellKey = tuple[str, int, str]


def _inside_ring(x: float, y: float, ring: Ring) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in pairwise(ring):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _distance_to_segment(x: float, y: float, start: Point, end: Point) -> float:
    (x1, y1), (x2, y2) = start, end
    dx, dy = x2 - x1, y2 - y1
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / length_squared))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def _accepts(x: float, y: float, rings: Sequence[Ring], setback_m: float) -> bool:
    outer, holes = rings[0], rings[1:]
    if not _inside_ring(x, y, outer) or any(_inside_ring(x, y, hole) for hole in holes):
        return False
    if setback_m <= 0:
        return True
    return all(
        _distance_to_segment(x, y, start, end) >= setback_m
        for ring in rings
        for start, end in pairwise(ring)
    )


def _parse_zone(feature: Mapping[str, Any]) -> tuple[CellKey, dict[str, Any], list[Ring]]:
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    road_code = properties.get("road_code")
    segment_index = properties.get("segment_index")
    zone = properties.get("zone")
    if not isinstance(road_code, str) or not road_code:
        raise ValueError("zone feature requires a road_code string")
    if isinstance(segment_index, bool) or not isinstance(segment_index, int) or segment_index < 0:
        raise ValueError("zone feature requires a non-negative integer segment_index")
    if zone not in ZONES:
        raise ValueError(f"zone must be one of {ZONES}")
    if geometry.get("type") != "Polygon":
        raise ValueError("zone geometry must be a GeoJSON Polygon in a metric CRS")
    coordinates = geometry.get("coordinates") or []
    rings = [[(float(x), float(y)) for x, y, *_ in ring] for ring in coordinates]
    if not rings or any(len(ring) < 4 or ring[0] != ring[-1] for ring in rings):
        raise ValueError("polygon rings must be closed with at least four positions")
    return (road_code, segment_index, zone), dict(properties), rings


def plan_campaign(
    zones: Iterable[Mapping[str, Any]],
    *,
    seed: int,
    campaign_id: str,
    points_per_cell: int = 3,
    substitutes: int = 3,
    edge_setback_m: float = 0.0,
    srid: int = 31983,
    max_attempts: int = 10_000,
) -> dict[str, Any]:
    if points_per_cell < 1 or substitutes < 0 or edge_setback_m < 0 or max_attempts < 1:
        raise ValueError("invalid sampling parameters")
    parsed = [_parse_zone(feature) for feature in zones]
    keys = [key for key, _, _ in parsed]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate road_code/segment_index/zone cell")

    cells = []
    wanted = points_per_cell + substitutes
    for (road_code, segment_index, zone), properties, rings in sorted(
        parsed, key=lambda item: (item[0][0], item[0][1], ZONES.index(item[0][2]))
    ):
        cell_key = f"{seed}:{road_code}:{segment_index}:{zone}"
        generator = random.Random(cell_key)
        xs = [x for x, _ in rings[0]]
        ys = [y for _, y in rings[0]]
        points = []
        for _ in range(max_attempts):
            if len(points) == wanted:
                break
            x = generator.uniform(min(xs), max(xs))
            y = generator.uniform(min(ys), max(ys))
            if _accepts(x, y, rings, edge_setback_m):
                rank = len(points) + 1
                points.append(
                    {
                        "planned_point_id": str(uuid.uuid5(_POINT_NAMESPACE, f"{cell_key}:{rank}")),
                        "rank": rank,
                        "role": "primary" if rank <= points_per_cell else "substitute",
                        "x": round(x, 3),
                        "y": round(y, 3),
                    }
                )
        data_status = properties.get("data_status")
        cells.append(
            {
                "road_code": road_code,
                "segment_index": segment_index,
                "zone": zone,
                "threshold_cm": 10 if zone == "special" else 30,
                "geometry_data_status": data_status,
                "eligible_for_field_use": data_status == "real",
                "strata": {
                    key: properties[key]
                    for key in ("historical_class", "surroundings")
                    if key in properties
                },
                "points": points,
                "shortfall": None if len(points) == wanted else "insufficient_area_after_setback",
            }
        )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "sampler_version": SAMPLER_VERSION,
        "campaign_id": campaign_id,
        "seed": seed,
        "srid": srid,
        "points_per_cell": points_per_cell,
        "substitutes": substitutes,
        "edge_setback_m": edge_setback_m,
        "authorizes_field_work": False,
        "summary": {
            "cells": len(cells),
            "primary_points": sum(
                1 for cell in cells for point in cell["points"] if point["role"] == "primary"
            ),
            "substitute_points": sum(
                1 for cell in cells for point in cell["points"] if point["role"] == "substitute"
            ),
            "cells_with_shortfall": sum(1 for cell in cells if cell["shortfall"]),
            "cells_not_eligible_for_field_use": sum(
                1 for cell in cells if not cell["eligible_for_field_use"]
            ),
        },
        "cells": cells,
    }
