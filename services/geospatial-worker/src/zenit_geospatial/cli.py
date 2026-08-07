from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from zenit_geospatial.import_catalog import InMemoryImportCatalog, identify_source, plan_import
from zenit_geospatial.km_markers import parse_km_markers
from zenit_geospatial.mowing_polygons import parse_mowing_polygons
from zenit_geospatial.postgres_import import PostgresImportRepository, execute_import
from zenit_geospatial.vegetation_workbook import parse_vegetation_workbook

PARSER_VERSION = "1.0.0"


def psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def import_source(source: Path, kind: str, database_url: str) -> tuple[str, str | None]:
    try:
        import psycopg
    except ImportError as error:
        raise RuntimeError("psycopg is required; install the project dependencies") from error

    parsers: dict[str, tuple[str, Any]] = {
        "km-markers": ("kmz", parse_km_markers),
        "mowing-polygons": ("kml", parse_mowing_polygons),
        "vegetation-workbook": ("xlsx", parse_vegetation_workbook),
    }
    detected_format, parser = parsers[kind]
    source_identity = identify_source(source, detected_format)
    plan = plan_import(
        source_identity,
        parser_name=kind,
        parser_version=PARSER_VERSION,
        catalog=InMemoryImportCatalog(),
    )
    repository = PostgresImportRepository(lambda: psycopg.connect(psycopg_url(database_url)))
    reservation, status = execute_import(repository, plan, parser)
    return reservation.decision.value, status.value if status is not None else None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import one immutable ZENIT source into staging")
    parser.add_argument(
        "kind",
        choices=("km-markers", "mowing-polygons", "vegetation-workbook"),
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    if not arguments.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")
    source = arguments.source.resolve()
    if not source.is_file():
        raise SystemExit(f"Source file does not exist: {source}")
    raw_directory = (Path.cwd() / "data" / "raw").resolve()
    if not source.is_relative_to(raw_directory):
        raise SystemExit(f"Source must be inside immutable raw directory: {raw_directory}")
    decision, status = import_source(source, arguments.kind, arguments.database_url)
    print(f"decision={decision} status={status or 'unchanged'}")


if __name__ == "__main__":
    main()
