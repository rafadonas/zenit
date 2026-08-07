from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from zenit_geospatial.km_markers import parse_km_markers
from zenit_geospatial.models import AnomalyCode, VegetationClass
from zenit_geospatial.mowing_polygons import parse_mowing_polygons
from zenit_geospatial.vegetation_workbook import (
    class_counts,
    compare_workbooks,
    parse_vegetation_workbook,
)

FIXTURES = Path(__file__).parent / "fixtures"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>
"""
ROOT_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""
WORKBOOK = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="ROÇADA" sheetId="1" r:id="rId1"/></sheets>
</workbook>
"""
WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""


def create_workbook(path: Path, second_class: int = 2) -> None:
    strings = ["ITEM", "DESCRIPTION", "1.1", "LEFT MARGIN", "X"]
    shared = "".join(f"<si><t>{value}</t></si>" for value in strings)
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"{shared}</sst>"
    )
    sheet = f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="6"><c r="BF6"><v>45744</v></c></row>
    <row r="9">
      <c r="A9" t="s"><v>0</v></c><c r="B9" t="s"><v>1</v></c>
      <c r="F9"><v>0</v></c><c r="G9"><v>500</v></c><c r="H9"><v>1000</v></c>
    </row>
    <row r="10">
      <c r="A10" t="s"><v>2</v></c><c r="B10" t="s"><v>3</v></c>
      <c r="F10"><v>1</v></c><c r="G10"><v>{second_class}</v></c>
      <c r="H10" t="s"><v>4</v></c>
    </row>
  </sheetData>
</worksheet>
"""
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("xl/workbook.xml", WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS)
        archive.writestr("xl/sharedStrings.xml", shared_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


class KmMarkerParserTests(unittest.TestCase):
    def test_parses_and_sorts_unordered_markers(self) -> None:
        result = parse_km_markers(FIXTURES / "km_markers_unordered.kml", range(2))

        self.assertFalse(result.has_errors)
        self.assertEqual([marker.kilometer for marker in result.records], [0, 1])
        self.assertIn(
            AnomalyCode.NON_SEQUENTIAL_SOURCE_ORDER,
            {anomaly.code for anomaly in result.anomalies},
        )


class MowingPolygonParserTests(unittest.TestCase):
    def test_preserves_raw_and_marks_shifted_mapping_as_inferred(self) -> None:
        result = parse_mowing_polygons(FIXTURES / "mowing_shifted_schema.kml")

        self.assertFalse(result.has_errors)
        self.assertEqual(len(result.records), 1)
        polygon = result.records[0]
        self.assertEqual(polygon.inferred_latitude, -23.45)
        self.assertEqual(polygon.inferred_longitude, -46.75)
        self.assertEqual(polygon.inferred_area_m2, 125.5)
        self.assertEqual(polygon.inference_status, "needs_validation")
        self.assertEqual(polygon.raw_attributes["classe"], "-23.45")
        self.assertIn(
            AnomalyCode.SHIFTED_ATTRIBUTE_MAPPING,
            {anomaly.code for anomaly in result.anomalies},
        )


class WorkbookParserTests(unittest.TestCase):
    def test_decodes_classes_and_internal_reference_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "version-a.xlsx"
            create_workbook(source)
            result = parse_vegetation_workbook(source)

        self.assertFalse(result.has_errors)
        workbook = result.records[0]
        self.assertEqual(workbook.reference_date.isoformat(), "2025-03-28")
        self.assertEqual(len(workbook.observations), 3)
        self.assertEqual(
            class_counts(workbook),
            {
                VegetationClass.N1: 1,
                VegetationClass.N2: 1,
                VegetationClass.NOT_APPLICABLE: 1,
            },
        )

    def test_compares_versions_without_treating_them_as_time_series(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            left_path = Path(directory) / "version-a.xlsx"
            right_path = Path(directory) / "version-b.xlsx"
            create_workbook(left_path, second_class=2)
            create_workbook(right_path, second_class=3)
            left = parse_vegetation_workbook(left_path).records[0]
            right = parse_vegetation_workbook(right_path).records[0]

            differences = compare_workbooks(left, right)

        self.assertEqual(len(differences), 1)
        self.assertEqual(differences[0].station_meter, 500)
        self.assertEqual(differences[0].left, VegetationClass.N2)
        self.assertEqual(differences[0].right, VegetationClass.N3)


if __name__ == "__main__":
    unittest.main()
