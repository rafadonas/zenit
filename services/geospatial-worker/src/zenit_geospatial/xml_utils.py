from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_kml_root(path: Path) -> tuple[ET.Element, bool]:
    """Return a KML root and whether the source was a real ZIP/KMZ container."""

    try:
        with ZipFile(path) as archive:
            candidates = sorted(
                name for name in archive.namelist() if name.lower().endswith(".kml")
            )
            if not candidates:
                raise ValueError("KMZ archive contains no KML document")
            return ET.fromstring(archive.read(candidates[0])), True
    except BadZipFile:
        return ET.fromstring(path.read_bytes()), False


def child_text(element: ET.Element, child_name: str) -> str | None:
    child = next((child for child in element if local_name(child.tag) == child_name), None)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def parse_coordinate_text(text: str | None) -> tuple[tuple[float, float], ...]:
    if not text:
        return ()
    coordinates = []
    for token in text.split():
        components = token.split(",")
        if len(components) < 2:
            continue
        coordinates.append((float(components[0]), float(components[1])))
    return tuple(coordinates)
