from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from zenit_geospatial.models import (
    Anomaly,
    AnomalyCode,
    Coordinate,
    KmMarker,
    ParseResult,
    Severity,
)
from zenit_geospatial.xml_utils import child_text, local_name, parse_coordinate_text, read_kml_root

KM_PATTERN = re.compile(r"(?P<road>[A-Z]{2}\s*[-]?\s*\d{3}).*?km\s*(?P<km>\d+)", re.I | re.S)


def parse_km_markers(path: Path, expected_range: range = range(30)) -> ParseResult[KmMarker]:
    result: ParseResult[KmMarker] = ParseResult(source_path=path)
    try:
        root, _ = read_kml_root(path)
    except (OSError, ValueError, ET.ParseError) as error:
        result.anomalies.append(Anomaly(AnomalyCode.INVALID_CONTAINER, Severity.ERROR, str(error)))
        return result

    placemarks = [element for element in root.iter() if local_name(element.tag) == "Placemark"]
    for index, placemark in enumerate(placemarks):
        description = child_text(placemark, "description") or ""
        match = KM_PATTERN.search(description)
        record_key = f"Placemark[{index}]"
        if not match:
            result.anomalies.append(
                Anomaly(
                    AnomalyCode.INVALID_KM_DESCRIPTION,
                    Severity.ERROR,
                    f"Could not parse road and kilometer from {description!r}",
                    record_key,
                )
            )
            continue
        coordinate_element = next(
            (element for element in placemark.iter() if local_name(element.tag) == "coordinates"),
            None,
        )
        try:
            coordinates = parse_coordinate_text(
                coordinate_element.text if coordinate_element is not None else None
            )
        except ValueError as error:
            coordinates = ()
            result.anomalies.append(
                Anomaly(AnomalyCode.INVALID_GEOMETRY, Severity.ERROR, str(error), record_key)
            )
        if len(coordinates) != 1:
            result.anomalies.append(
                Anomaly(
                    AnomalyCode.INVALID_GEOMETRY,
                    Severity.ERROR,
                    f"Expected one Point coordinate, found {len(coordinates)}",
                    record_key,
                )
            )
            continue
        longitude, latitude = coordinates[0]
        road_code = re.sub(r"\s|-", "", match.group("road")).upper()
        result.records.append(
            KmMarker(
                source_index=index,
                road_code=road_code,
                kilometer=int(match.group("km")),
                coordinate=Coordinate(longitude=longitude, latitude=latitude),
                raw_description=description,
            )
        )

    kilometers = [marker.kilometer for marker in result.records]
    duplicates = sorted(km for km in set(kilometers) if kilometers.count(km) > 1)
    for kilometer in duplicates:
        result.anomalies.append(
            Anomaly(
                AnomalyCode.DUPLICATE_KM,
                Severity.ERROR,
                f"Kilometer {kilometer} occurs more than once",
            )
        )
    if kilometers != sorted(kilometers):
        result.anomalies.append(
            Anomaly(
                AnomalyCode.NON_SEQUENTIAL_SOURCE_ORDER,
                Severity.WARNING,
                "Marker source order is not ascending; records must be sorted after parsing",
            )
        )
    missing = sorted(set(expected_range) - set(kilometers))
    if missing:
        result.anomalies.append(
            Anomaly(
                AnomalyCode.MISSING_EXPECTED_KM,
                Severity.ERROR,
                f"Missing expected kilometers: {missing}",
            )
        )
    result.records.sort(key=lambda marker: marker.kilometer)
    return result
