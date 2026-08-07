from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from zenit_geospatial.cli import psycopg_url
from zenit_geospatial.import_catalog import (
    ImportDecision,
    ImportStatus,
    InMemoryImportCatalog,
    identify_source,
    plan_import,
)
from zenit_geospatial.km_markers import parse_km_markers
from zenit_geospatial.mowing_polygons import parse_mowing_polygons
from zenit_geospatial.postgres_import import (
    ImportReservation,
    anomaly_rows,
    execute_import,
    polygon_wkt,
    staging_batch,
)

FIXTURES = Path(__file__).parent / "fixtures"


class StagingSerializationTests(unittest.TestCase):
    def test_converts_sqlalchemy_psycopg_url_for_driver(self) -> None:
        self.assertEqual(
            psycopg_url("postgresql+psycopg://zenit:secret@postgres/zenit"),
            "postgresql://zenit:secret@postgres/zenit",
        )

    def test_serializes_marker_rows_without_losing_source_index(self) -> None:
        result = parse_km_markers(FIXTURES / "km_markers_unordered.kml", range(2))

        batch = staging_batch(result)

        self.assertEqual(batch.table, "staging_km_marker")
        self.assertEqual(len(batch.rows), 2)
        self.assertEqual(batch.rows[0][2], 0)
        self.assertEqual(batch.rows[0][4:], (-46.7, -23.4))
        warnings = anomaly_rows(result.anomalies)
        self.assertEqual(warnings[0][0], "non_sequential_source_order")

    def test_serializes_polygon_as_parameterized_wkt_and_raw_json(self) -> None:
        result = parse_mowing_polygons(FIXTURES / "mowing_shifted_schema.kml")

        batch = staging_batch(result)
        wkt = polygon_wkt(result.records[0])

        self.assertEqual(batch.table, "staging_mowing_polygon")
        self.assertTrue(wkt.startswith("POLYGON(("))
        self.assertTrue(wkt.endswith("))"))
        self.assertIn('"classe": "-23.45"', batch.rows[0][3])
        self.assertEqual(batch.rows[0][-1], "needs_validation")


class FakeRepository:
    def __init__(self, decision: ImportDecision = ImportDecision.PLANNED) -> None:
        self.decision = decision
        self.events: list[str] = []

    def reserve(self, _: Any) -> ImportReservation:
        self.events.append("reserve")
        previous = (
            ImportStatus.SUCCEEDED if self.decision == ImportDecision.ALREADY_SUCCEEDED else None
        )
        return ImportReservation(self.decision, "job-1", "run-1", 1, previous)

    def mark_running(self, _: ImportReservation) -> None:
        self.events.append("running")

    def persist_result(self, _: ImportReservation, result: Any) -> ImportStatus:
        self.events.append(f"persist:{len(result.records)}")
        return ImportStatus.SUCCEEDED

    def mark_failed(self, _: ImportReservation) -> None:
        self.events.append("failed")


class ImportExecutionTests(unittest.TestCase):
    def make_plan(self, path: Path) -> Any:
        source = identify_source(path, "kml")
        return plan_import(source, "km-markers", "1.0.0", InMemoryImportCatalog())

    def test_runs_parser_between_running_and_atomic_persistence(self) -> None:
        repository = FakeRepository()
        plan = self.make_plan(FIXTURES / "km_markers_unordered.kml")

        _, status = execute_import(
            repository,  # type: ignore[arg-type]
            plan,
            lambda path: parse_km_markers(path, range(2)),
        )

        self.assertEqual(status, ImportStatus.SUCCEEDED)
        self.assertEqual(repository.events, ["reserve", "running", "persist:2"])

    def test_marks_attempt_failed_when_parser_raises(self) -> None:
        repository = FakeRepository()
        plan = self.make_plan(FIXTURES / "km_markers_unordered.kml")

        def broken_parser(_: Path) -> Any:
            raise RuntimeError("broken")

        with self.assertRaisesRegex(RuntimeError, "broken"):
            execute_import(repository, plan, broken_parser)  # type: ignore[arg-type]

        self.assertEqual(repository.events, ["reserve", "running", "failed"])

    def test_skips_already_successful_job(self) -> None:
        repository = FakeRepository(ImportDecision.ALREADY_SUCCEEDED)
        plan = self.make_plan(FIXTURES / "km_markers_unordered.kml")

        _, status = execute_import(
            repository,  # type: ignore[arg-type]
            plan,
            lambda path: parse_km_markers(path, range(2)),
        )

        self.assertEqual(status, ImportStatus.SUCCEEDED)
        self.assertEqual(repository.events, ["reserve"])


if __name__ == "__main__":
    unittest.main()
