import tempfile
import unittest
from pathlib import Path

from scripts.audit_sources import audit_kml, build_manifest, detect_format

SAMPLE_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Manual</name>
      <description>SP021 km 2</description>
      <ExtendedData><Data name="area"><value>12.5</value></Data></ExtendedData>
      <Point><coordinates>-46.75,-23.45,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>
"""


class SourceAuditTests(unittest.TestCase):
    def test_plain_kml_is_detected_and_summarized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "misnamed.kmz"
            source.write_bytes(SAMPLE_KML)

            self.assertEqual(detect_format(source), "kml")
            details = audit_kml(source, "kml")

        self.assertEqual(details["placemark_count"], 1)
        self.assertEqual(details["geometry_counts"], {"Point": 1})
        self.assertEqual(details["placemark_names"], {"Manual": 1})
        self.assertEqual(details["numeric_field_stats"]["area"]["sum"], 12.5)

    def test_manifest_excludes_gitkeep_and_hashes_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_directory = Path(directory)
            (raw_directory / ".gitkeep").write_text("", encoding="utf-8")
            (raw_directory / "sample.kml").write_bytes(SAMPLE_KML)

            manifest = build_manifest(raw_directory)

        self.assertEqual(manifest["file_count"], 1)
        self.assertEqual(manifest["files"][0]["path"], "sample.kml")
        self.assertEqual(len(manifest["files"][0]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
