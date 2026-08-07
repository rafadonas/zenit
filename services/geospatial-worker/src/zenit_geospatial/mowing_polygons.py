from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from zenit_geospatial.models import (
    Anomaly,
    AnomalyCode,
    Coordinate,
    MowingPolygon,
    ParseResult,
    Severity,
)
from zenit_geospatial.xml_utils import child_text, local_name, parse_coordinate_text, read_kml_root


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def extended_attributes(placemark: ET.Element) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for element in placemark.iter():
        if local_name(element.tag) not in {"SimpleData", "Data"}:
            continue
        name = element.attrib.get("name")
        if not name:
            continue
        value_element = next((child for child in element if local_name(child.tag) == "value"), None)
        value = value_element.text if value_element is not None else element.text
        attributes[name] = (value or "").strip()
    return attributes


def parse_mowing_polygons(path: Path) -> ParseResult[MowingPolygon]:
    result: ParseResult[MowingPolygon] = ParseResult(source_path=path)
    try:
        root, is_archive = read_kml_root(path)
    except (OSError, ValueError, ET.ParseError) as error:
        result.anomalies.append(Anomaly(AnomalyCode.INVALID_CONTAINER, Severity.ERROR, str(error)))
        return result
    if path.suffix.lower() == ".kmz" and not is_archive:
        result.anomalies.append(
            Anomaly(
                AnomalyCode.EXTENSION_CONTENT_MISMATCH,
                Severity.WARNING,
                "File has .kmz extension but contains uncompressed KML/XML",
            )
        )

    placemarks = [element for element in root.iter() if local_name(element.tag) == "Placemark"]
    shifted_mapping_seen = False
    for index, placemark in enumerate(placemarks):
        record_key = f"Placemark[{index}]"
        attributes = extended_attributes(placemark)
        latitude = to_float(attributes.get("classe"))
        longitude = to_float(attributes.get("KM"))
        area = to_float(attributes.get("Latitude"))
        if latitude is not None and longitude is not None and area is not None:
            shifted_mapping_seen = True
        else:
            result.anomalies.append(
                Anomaly(
                    AnomalyCode.MISSING_ATTRIBUTE,
                    Severity.WARNING,
                    "Could not infer latitude, longitude, and area from shifted fields",
                    record_key,
                )
            )

        rings = []
        try:
            for element in placemark.iter():
                if local_name(element.tag) != "LinearRing":
                    continue
                coordinate_element = next(
                    (child for child in element.iter() if local_name(child.tag) == "coordinates"),
                    None,
                )
                raw_coordinates = parse_coordinate_text(
                    coordinate_element.text if coordinate_element is not None else None
                )
                rings.append(
                    tuple(
                        Coordinate(longitude=longitude_value, latitude=latitude_value)
                        for longitude_value, latitude_value in raw_coordinates
                    )
                )
        except ValueError as error:
            result.anomalies.append(
                Anomaly(AnomalyCode.INVALID_GEOMETRY, Severity.ERROR, str(error), record_key)
            )
        if not rings or any(len(ring) < 4 or ring[0] != ring[-1] for ring in rings):
            result.anomalies.append(
                Anomaly(
                    AnomalyCode.INVALID_GEOMETRY,
                    Severity.ERROR,
                    "Polygon has no closed LinearRing with at least four coordinates",
                    record_key,
                )
            )
            continue

        raw_kilometer = child_text(placemark, "description")
        try:
            kilometer_hint = int(raw_kilometer) if raw_kilometer is not None else None
        except ValueError:
            kilometer_hint = None
            result.anomalies.append(
                Anomaly(
                    AnomalyCode.INVALID_ATTRIBUTE,
                    Severity.WARNING,
                    f"Invalid kilometer hint: {raw_kilometer!r}",
                    record_key,
                )
            )
        result.records.append(
            MowingPolygon(
                source_index=index,
                equipment_class=child_text(placemark, "name") or "unknown",
                kilometer_hint=kilometer_hint,
                rings=tuple(rings),
                raw_attributes=attributes,
                inferred_latitude=latitude,
                inferred_longitude=longitude,
                inferred_area_m2=area,
            )
        )

    if shifted_mapping_seen:
        result.anomalies.append(
            Anomaly(
                AnomalyCode.SHIFTED_ATTRIBUTE_MAPPING,
                Severity.WARNING,
                "Inferred classe->latitude, KM->longitude, Latitude->area; validation required",
            )
        )
    return result
