#!/usr/bin/env python3
"""Audit immutable ZENIT source files using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

KML_NAMESPACE = "http://www.opengis.net/kml/2.2"
MAIN_SPREADSHEET_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_RELATIONSHIP_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/relationships"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def detect_format(path: Path) -> str:
    header = path.read_bytes()[:8]
    if header.startswith(b"PK\x03\x04"):
        with ZipFile(path) as archive:
            names = set(archive.namelist())
        if "[Content_Types].xml" in names and "xl/workbook.xml" in names:
            return "xlsx"
        if "[Content_Types].xml" in names and "word/document.xml" in names:
            return "docx"
        if any(name.lower().endswith(".kml") for name in names):
            return "kmz"
        return "zip"
    if header.startswith(b"%PDF"):
        return "pdf"
    if header.lstrip().startswith(b"<?xml") or header.lstrip().startswith(b"<kml"):
        return "kml"
    return mimetypes.guess_type(path.name)[0] or "unknown"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def coordinate_tuples(text: str | None) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    if not text:
        return points
    for token in text.split():
        values = token.split(",")
        if len(values) >= 2:
            try:
                points.append((float(values[0]), float(values[1])))
            except ValueError:
                continue
    return points


def audit_kml_bytes(content: bytes) -> dict[str, Any]:
    root = ET.fromstring(content)
    placemarks = [element for element in root.iter() if local_name(element.tag) == "Placemark"]
    geometry_counts: Counter[str] = Counter()
    names: Counter[str] = Counter()
    descriptions: Counter[str] = Counter()
    field_presence: Counter[str] = Counter()
    field_values: dict[str, Counter[str]] = {}
    coordinates: list[tuple[float, float]] = []

    for placemark in placemarks:
        for element in placemark.iter():
            kind = local_name(element.tag)
            if kind in {"Point", "LineString", "Polygon", "MultiGeometry"}:
                geometry_counts[kind] += 1
            elif kind == "coordinates":
                coordinates.extend(coordinate_tuples(element.text))
            elif kind in {"SimpleData", "Data"}:
                field_name = element.attrib.get("name", "<unnamed>")
                value_element = next(
                    (child for child in element if local_name(child.tag) == "value"), None
                )
                value = (value_element.text if value_element is not None else element.text) or ""
                field_presence[field_name] += 1
                field_values.setdefault(field_name, Counter())[value.strip()] += 1

        name_element = next(
            (element for element in placemark if local_name(element.tag) == "name"), None
        )
        if name_element is not None and name_element.text:
            names[name_element.text.strip()] += 1
        description_element = next(
            (element for element in placemark if local_name(element.tag) == "description"), None
        )
        if description_element is not None and description_element.text:
            descriptions[description_element.text.strip()] += 1

    bounds = None
    if coordinates:
        longitudes = [coordinate[0] for coordinate in coordinates]
        latitudes = [coordinate[1] for coordinate in coordinates]
        bounds = {
            "min_longitude": min(longitudes),
            "min_latitude": min(latitudes),
            "max_longitude": max(longitudes),
            "max_latitude": max(latitudes),
        }

    return {
        "placemark_count": len(placemarks),
        "geometry_counts": dict(sorted(geometry_counts.items())),
        "coordinate_bounds": bounds,
        "placemark_names": dict(names.most_common()),
        "placemark_descriptions": dict(descriptions.most_common()),
        "field_presence": dict(sorted(field_presence.items())),
        "field_sample_values": {
            field: [value for value, _ in values.most_common(5)]
            for field, values in sorted(field_values.items())
        },
        "numeric_field_stats": {
            field: {
                "count": len(numbers),
                "minimum": min(numbers),
                "maximum": max(numbers),
                "sum": sum(numbers),
            }
            for field, values in sorted(field_values.items())
            if (
                numbers := [
                    number
                    for value in values.elements()
                    for number in [parse_float(value)]
                    if number is not None
                ]
            )
        },
    }


def parse_float(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def audit_kml(path: Path, source_format: str) -> dict[str, Any]:
    if source_format == "kml":
        return audit_kml_bytes(path.read_bytes())
    with ZipFile(path) as archive:
        kml_names = sorted(name for name in archive.namelist() if name.lower().endswith(".kml"))
        return {
            "archive_members": archive.namelist(),
            "kml_documents": {name: audit_kml_bytes(archive.read(name)) for name in kml_names},
        }


def column_number(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference)
    if not letters:
        return 0
    result = 0
    for character in letters.group(0):
        result = result * 26 + ord(character) - ord("A") + 1
    return result


def audit_xlsx(path: Path) -> dict[str, Any]:
    spreadsheet_ns = {"s": MAIN_SPREADSHEET_NAMESPACE}
    relationship_key = f"{{{OFFICE_RELATIONSHIP_NAMESPACE}}}id"
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            relationship.attrib["Id"]: relationship.attrib["Target"]
            for relationship in relationships.findall(
                f"{{{PACKAGE_RELATIONSHIP_NAMESPACE}}}Relationship"
            )
        }
        sheets: list[dict[str, Any]] = []
        for sheet in workbook.findall("s:sheets/s:sheet", spreadsheet_ns):
            target = targets[sheet.attrib[relationship_key]].lstrip("/")
            if not target.startswith("xl/"):
                target = f"xl/{target}"
            worksheet_bytes = archive.read(target)
            worksheet = ET.fromstring(worksheet_bytes)
            rows = worksheet.findall("s:sheetData/s:row", spreadsheet_ns)
            cells = worksheet.findall(".//s:c", spreadsheet_ns)
            max_column = max((column_number(cell.attrib.get("r", "")) for cell in cells), default=0)
            sheets.append(
                {
                    "name": sheet.attrib["name"],
                    "row_count": len(rows),
                    "max_column": max_column,
                    "cell_count": len(cells),
                    "merged_range_count": len(
                        worksheet.findall("s:mergeCells/s:mergeCell", spreadsheet_ns)
                    ),
                    "contains_serial_45744": b"45744" in worksheet_bytes,
                }
            )
        return {"sheets": sheets, "archive_member_count": len(archive.namelist())}


def audit_archive(path: Path, source_format: str) -> dict[str, Any] | None:
    try:
        if source_format in {"kml", "kmz"}:
            return audit_kml(path, source_format)
        if source_format == "xlsx":
            return audit_xlsx(path)
        if source_format == "docx":
            with ZipFile(path) as archive:
                document = ET.fromstring(archive.read("word/document.xml"))
            paragraphs = []
            for paragraph in document.iter():
                if local_name(paragraph.tag) != "p":
                    continue
                text = "".join(
                    node.text or "" for node in paragraph.iter() if local_name(node.tag) == "t"
                ).strip()
                if text:
                    paragraphs.append(text)
            return {"paragraph_count": len(paragraphs), "heading_sample": paragraphs[:10]}
    except (BadZipFile, ET.ParseError, KeyError) as error:
        return {"audit_error": f"{type(error).__name__}: {error}"}
    return None


def build_manifest(raw_directory: Path) -> dict[str, Any]:
    files = []
    for path in sorted(raw_directory.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        source_format = detect_format(path)
        files.append(
            {
                "path": path.relative_to(raw_directory).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "detected_format": source_format,
                "details": audit_archive(path, source_format),
            }
        )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "raw_directory": raw_directory.as_posix(),
        "file_count": len(files),
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    manifest = build_manifest(arguments.raw_dir)
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
