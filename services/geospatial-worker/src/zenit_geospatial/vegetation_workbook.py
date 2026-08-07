from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from zenit_geospatial.models import (
    Anomaly,
    AnomalyCode,
    ParseResult,
    Severity,
    VegetationClass,
    VegetationObservation,
    WorkbookDifference,
    WorkbookVersion,
)

SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
EXPECTED_REFERENCE_DATE = date(2025, 3, 28)


def column_number(reference: str) -> int:
    match = re.match(r"[A-Z]+", reference)
    if not match:
        raise ValueError(f"Invalid cell reference: {reference!r}")
    number = 0
    for character in match.group(0):
        number = number * 26 + ord(character) - ord("A") + 1
    return number


def excel_date(serial: int) -> date:
    return date(1899, 12, 30) + timedelta(days=serial)


def shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(node.text or "" for node in item.iter() if node.tag.endswith("}t")) for item in root
    ]


def decoded_cells(worksheet: ET.Element, strings: list[str]) -> dict[str, str]:
    namespace = {"s": SHEET_NS}
    cells: dict[str, str] = {}
    for cell in worksheet.findall(".//s:c", namespace):
        reference = cell.attrib.get("r")
        if not reference:
            continue
        value_node = cell.find("s:v", namespace)
        if value_node is None or value_node.text is None:
            continue
        value = value_node.text
        if cell.attrib.get("t") == "s":
            try:
                value = strings[int(value)]
            except (IndexError, ValueError):
                continue
        cells[reference] = value
    return cells


def workbook_sheets(archive: ZipFile) -> list[tuple[str, str]]:
    namespace = {"s": SHEET_NS}
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        relation.attrib["Id"]: relation.attrib["Target"]
        for relation in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
    }
    relationship_key = f"{{{OFFICE_REL_NS}}}id"
    sheets = []
    for sheet in workbook.findall("s:sheets/s:sheet", namespace):
        target = targets[sheet.attrib[relationship_key]].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        sheets.append((sheet.attrib["name"], target))
    return sheets


def classification(value: str) -> VegetationClass | None:
    normalized = value.strip().upper()
    mapping = {
        "1": VegetationClass.N1,
        "1.0": VegetationClass.N1,
        "2": VegetationClass.N2,
        "2.0": VegetationClass.N2,
        "3": VegetationClass.N3,
        "3.0": VegetationClass.N3,
        "X": VegetationClass.NOT_APPLICABLE,
        "N/A": VegetationClass.NOT_APPLICABLE,
    }
    return mapping.get(normalized)


def parse_vegetation_workbook(path: Path) -> ParseResult[WorkbookVersion]:
    result: ParseResult[WorkbookVersion] = ParseResult(source_path=path)
    try:
        with ZipFile(path) as archive:
            strings = shared_strings(archive)
            sheets = workbook_sheets(archive)
            mowing_sheet = next((sheet for sheet in sheets if sheet[0].strip() == "ROÇADA"), None)
            if mowing_sheet is None:
                raise ValueError("Workbook has no ROÇADA sheet")
            sheet_name, target = mowing_sheet
            worksheet = ET.fromstring(archive.read(target))
            cells = decoded_cells(worksheet, strings)
    except (BadZipFile, ET.ParseError, KeyError, OSError, ValueError) as error:
        result.anomalies.append(
            Anomaly(AnomalyCode.INVALID_WORKBOOK_STRUCTURE, Severity.ERROR, str(error))
        )
        return result

    reference_serial = next(
        (int(float(value)) for value in cells.values() if value.strip() == "45744"),
        None,
    )
    if reference_serial is None:
        result.anomalies.append(
            Anomaly(
                AnomalyCode.UNEXPECTED_REFERENCE_DATE,
                Severity.ERROR,
                "Expected internal survey serial 45744 was not found",
            )
        )
        return result
    reference_date = excel_date(reference_serial)
    if reference_date != EXPECTED_REFERENCE_DATE:
        result.anomalies.append(
            Anomaly(
                AnomalyCode.UNEXPECTED_REFERENCE_DATE,
                Severity.ERROR,
                f"Expected {EXPECTED_REFERENCE_DATE}, decoded {reference_date}",
            )
        )

    header_row = next(
        (
            int(re.search(r"\d+", reference).group())
            for reference, value in cells.items()
            if value.strip().upper() == "ITEM"
        ),
        None,
    )
    if header_row is None:
        result.anomalies.append(
            Anomaly(
                AnomalyCode.INVALID_WORKBOOK_STRUCTURE,
                Severity.ERROR,
                "Could not locate ITEM header row",
            )
        )
        return result

    stations: dict[int, int] = {}
    for reference, value in cells.items():
        match = re.fullmatch(r"([A-Z]+)(\d+)", reference)
        if not match or int(match.group(2)) != header_row:
            continue
        column = column_number(reference)
        if column < 6:
            continue
        try:
            stations[column] = int(float(value))
        except ValueError:
            continue

    observations = []
    data_rows = sorted(
        {
            int(match.group(1))
            for reference in cells
            if (match := re.fullmatch(r"A(\d+)", reference))
            and int(match.group(1)) > header_row
            and re.fullmatch(r"\d+\.\d+", cells[reference].strip())
        }
    )
    for row in data_rows:
        item_code = cells[f"A{row}"].strip()
        description = cells.get(f"B{row}", "").strip()
        for reference, raw_value in cells.items():
            match = re.fullmatch(r"([A-Z]+)(\d+)", reference)
            if not match or int(match.group(2)) != row:
                continue
            column = column_number(reference)
            if column not in stations:
                continue
            parsed_class = classification(raw_value)
            if parsed_class is None:
                result.anomalies.append(
                    Anomaly(
                        AnomalyCode.INVALID_CLASSIFICATION,
                        Severity.ERROR,
                        f"Unexpected class value {raw_value!r}",
                        reference,
                    )
                )
                continue
            observations.append(
                VegetationObservation(
                    item_code=item_code,
                    description=description,
                    station_meter=stations[column],
                    vegetation_class=parsed_class,
                    source_cell=reference,
                )
            )

    if not observations:
        result.anomalies.append(
            Anomaly(
                AnomalyCode.INVALID_WORKBOOK_STRUCTURE,
                Severity.ERROR,
                "No classification observations were decoded",
            )
        )
        return result
    result.records.append(
        WorkbookVersion(
            version_label=path.stem,
            sheet_name=sheet_name,
            reference_date=reference_date,
            observations=tuple(observations),
        )
    )
    return result


def compare_workbooks(
    left: WorkbookVersion, right: WorkbookVersion
) -> tuple[WorkbookDifference, ...]:
    left_index = {
        (observation.item_code, observation.station_meter): observation
        for observation in left.observations
    }
    right_index = {
        (observation.item_code, observation.station_meter): observation
        for observation in right.observations
    }
    differences = []
    for key in sorted(left_index.keys() & right_index.keys()):
        left_observation = left_index[key]
        right_observation = right_index[key]
        if left_observation.vegetation_class != right_observation.vegetation_class:
            differences.append(
                WorkbookDifference(
                    item_code=key[0],
                    station_meter=key[1],
                    left=left_observation.vegetation_class,
                    right=right_observation.vegetation_class,
                )
            )
    return tuple(differences)


def class_counts(workbook: WorkbookVersion) -> Counter[VegetationClass]:
    return Counter(observation.vegetation_class for observation in workbook.observations)
