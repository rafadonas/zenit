from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AnomalyCode(StrEnum):
    INVALID_CONTAINER = "invalid_container"
    INVALID_XML = "invalid_xml"
    MISSING_KML = "missing_kml"
    INVALID_GEOMETRY = "invalid_geometry"
    INVALID_KM_DESCRIPTION = "invalid_km_description"
    DUPLICATE_KM = "duplicate_km"
    NON_SEQUENTIAL_SOURCE_ORDER = "non_sequential_source_order"
    MISSING_EXPECTED_KM = "missing_expected_km"
    EXTENSION_CONTENT_MISMATCH = "extension_content_mismatch"
    SHIFTED_ATTRIBUTE_MAPPING = "shifted_attribute_mapping"
    MISSING_ATTRIBUTE = "missing_attribute"
    INVALID_ATTRIBUTE = "invalid_attribute"
    INVALID_WORKBOOK_STRUCTURE = "invalid_workbook_structure"
    UNEXPECTED_REFERENCE_DATE = "unexpected_reference_date"
    INVALID_CLASSIFICATION = "invalid_classification"


@dataclass(frozen=True, slots=True)
class Anomaly:
    code: AnomalyCode
    severity: Severity
    message: str
    source_record: str | None = None


@dataclass(slots=True)
class ParseResult[T]:
    source_path: Path
    records: list[T] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(anomaly.severity == Severity.ERROR for anomaly in self.anomalies)


@dataclass(frozen=True, slots=True)
class Coordinate:
    longitude: float
    latitude: float


@dataclass(frozen=True, slots=True)
class KmMarker:
    source_index: int
    road_code: str
    kilometer: int
    coordinate: Coordinate
    raw_description: str


@dataclass(frozen=True, slots=True)
class MowingPolygon:
    source_index: int
    equipment_class: str
    kilometer_hint: int | None
    rings: tuple[tuple[Coordinate, ...], ...]
    raw_attributes: dict[str, str]
    inferred_latitude: float | None
    inferred_longitude: float | None
    inferred_area_m2: float | None
    inference_status: str = "needs_validation"


class VegetationClass(StrEnum):
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"
    NOT_APPLICABLE = "X"


@dataclass(frozen=True, slots=True)
class VegetationObservation:
    item_code: str
    description: str
    station_meter: int
    vegetation_class: VegetationClass
    source_cell: str


@dataclass(frozen=True, slots=True)
class WorkbookVersion:
    version_label: str
    sheet_name: str
    reference_date: date
    observations: tuple[VegetationObservation, ...]


@dataclass(frozen=True, slots=True)
class WorkbookDifference:
    item_code: str
    station_meter: int
    left: VegetationClass
    right: VegetationClass
