from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from zenit_geospatial.import_catalog import ImportDecision, ImportPlan, ImportStatus
from zenit_geospatial.models import (
    Anomaly,
    KmMarker,
    MowingPolygon,
    ParseResult,
    WorkbookVersion,
)


class Cursor(Protocol):
    def execute(self, query: str, parameters: Sequence[Any] | None = None) -> Any: ...

    def executemany(self, query: str, parameters: Iterable[Sequence[Any]]) -> Any: ...

    def fetchone(self) -> Sequence[Any] | None: ...

    def __enter__(self) -> Cursor: ...

    def __exit__(self, *args: Any) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...

    def transaction(self) -> AbstractContextManager[Any]: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ImportReservation:
    decision: ImportDecision
    job_id: Any
    run_id: Any | None
    attempt_number: int | None
    previous_status: ImportStatus | None


@dataclass(frozen=True, slots=True)
class StagingBatch:
    table: str
    rows: tuple[tuple[Any, ...], ...]


def polygon_wkt(polygon: MowingPolygon) -> str:
    rings = []
    for ring in polygon.rings:
        coordinates = ", ".join(
            f"{coordinate.longitude:.15g} {coordinate.latitude:.15g}" for coordinate in ring
        )
        rings.append(f"({coordinates})")
    return f"POLYGON({', '.join(rings)})"


def staging_batch(result: ParseResult[Any]) -> StagingBatch:
    if not result.records:
        return StagingBatch(table="none", rows=())
    first = result.records[0]
    if isinstance(first, KmMarker):
        return StagingBatch(
            table="staging_km_marker",
            rows=tuple(
                (
                    record.source_index,
                    record.road_code,
                    record.kilometer,
                    record.raw_description,
                    record.coordinate.longitude,
                    record.coordinate.latitude,
                )
                for record in result.records
            ),
        )
    if isinstance(first, MowingPolygon):
        return StagingBatch(
            table="staging_mowing_polygon",
            rows=tuple(
                (
                    record.source_index,
                    record.equipment_class,
                    record.kilometer_hint,
                    json.dumps(record.raw_attributes, ensure_ascii=False, sort_keys=True),
                    polygon_wkt(record),
                    record.inferred_latitude,
                    record.inferred_longitude,
                    record.inferred_area_m2,
                    record.inference_status,
                )
                for record in result.records
            ),
        )
    if isinstance(first, WorkbookVersion):
        workbook_rows = []
        for workbook in result.records:
            for observation in workbook.observations:
                workbook_rows.append(
                    (
                        workbook.version_label,
                        workbook.sheet_name,
                        workbook.reference_date,
                        observation.item_code,
                        observation.description,
                        observation.station_meter,
                        observation.vegetation_class.value,
                        observation.source_cell,
                    )
                )
        return StagingBatch(
            table="staging_vegetation_observation",
            rows=tuple(workbook_rows),
        )
    raise TypeError(f"Unsupported parser record type: {type(first).__name__}")


def anomaly_rows(anomalies: Iterable[Anomaly]) -> tuple[tuple[str, str, str | None, str], ...]:
    return tuple(
        (anomaly.code.value, anomaly.severity.value, anomaly.source_record, anomaly.message)
        for anomaly in anomalies
    )


class PostgresImportRepository:
    """Transactional persistence adapter compatible with psycopg 3 connections."""

    def __init__(self, connection_factory: Callable[[], Connection]) -> None:
        self._connection_factory = connection_factory

    def reserve(self, plan: ImportPlan) -> ImportReservation:
        connection = self._connection_factory()
        try:
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO source_file (
                        sha256, original_path, original_name, size_bytes,
                        detected_format, storage_uri
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sha256) DO NOTHING
                    """,
                    (
                        plan.source.sha256,
                        plan.source.path.as_posix(),
                        plan.source.path.name,
                        plan.source.size_bytes,
                        plan.source.detected_format,
                        plan.source.path.resolve().as_uri(),
                    ),
                )
                cursor.execute(
                    "SELECT id FROM source_file WHERE sha256 = %s",
                    (plan.source.sha256,),
                )
                source_row = cursor.fetchone()
                if source_row is None:
                    raise RuntimeError("Could not resolve source_file after insert")
                source_id = source_row[0]
                cursor.execute(
                    """
                    INSERT INTO import_job (
                        source_file_id, parser_name, parser_version, parameters, idempotency_key
                    ) VALUES (%s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """,
                    (
                        source_id,
                        plan.identity.parser_name,
                        plan.identity.parser_version,
                        json.dumps(plan.identity.parameters, sort_keys=True),
                        plan.identity.idempotency_key,
                    ),
                )
                cursor.execute(
                    "SELECT id FROM import_job WHERE idempotency_key = %s FOR UPDATE",
                    (plan.identity.idempotency_key,),
                )
                job_row = cursor.fetchone()
                if job_row is None:
                    raise RuntimeError("Could not resolve import_job after insert")
                job_id = job_row[0]
                cursor.execute(
                    """
                    SELECT attempt_number, status
                    FROM import_run
                    WHERE import_job_id = %s
                    ORDER BY attempt_number DESC
                    LIMIT 1
                    """,
                    (job_id,),
                )
                latest = cursor.fetchone()
                previous_status = ImportStatus(latest[1]) if latest is not None else None
                if previous_status == ImportStatus.SUCCEEDED:
                    return ImportReservation(
                        ImportDecision.ALREADY_SUCCEEDED,
                        job_id,
                        None,
                        None,
                        previous_status,
                    )
                if previous_status in {ImportStatus.PENDING, ImportStatus.RUNNING}:
                    return ImportReservation(
                        ImportDecision.IN_PROGRESS,
                        job_id,
                        None,
                        None,
                        previous_status,
                    )
                attempt_number = (int(latest[0]) + 1) if latest is not None else 1
                decision = (
                    ImportDecision.RETRY_FAILED if latest is not None else ImportDecision.PLANNED
                )
                cursor.execute(
                    """
                    INSERT INTO import_run (import_job_id, attempt_number, status)
                    VALUES (%s, %s, 'pending')
                    RETURNING id
                    """,
                    (job_id, attempt_number),
                )
                run_row = cursor.fetchone()
                if run_row is None:
                    raise RuntimeError("Could not create import_run")
                return ImportReservation(
                    decision,
                    job_id,
                    run_row[0],
                    attempt_number,
                    previous_status,
                )
        finally:
            connection.close()

    def mark_running(self, reservation: ImportReservation) -> None:
        if reservation.run_id is None:
            raise ValueError("Reservation has no executable run")
        self._update_status(reservation.run_id, ImportStatus.RUNNING)

    def persist_result(
        self,
        reservation: ImportReservation,
        result: ParseResult[Any],
    ) -> ImportStatus:
        if reservation.run_id is None:
            raise ValueError("Reservation has no executable run")
        run_id = reservation.run_id
        batch = staging_batch(result)
        final_status = ImportStatus.REJECTED if result.has_errors else ImportStatus.SUCCEEDED
        connection = self._connection_factory()
        try:
            with connection.transaction(), connection.cursor() as cursor:
                anomalies = anomaly_rows(result.anomalies)
                if anomalies:
                    cursor.executemany(
                        """
                        INSERT INTO import_anomaly (
                            import_run_id, code, severity, source_record, message
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        ((run_id, *row) for row in anomalies),
                    )
                if not result.has_errors and batch.rows:
                    self._insert_staging(cursor, run_id, batch)
                geometry_warning_count = self._record_geometry_anomalies(
                    cursor, run_id, batch.table
                )
                cursor.execute(
                    """
                    UPDATE import_run
                    SET status = %s, record_count = %s, warning_count = %s,
                        error_count = %s, finished_at = now()
                    WHERE id = %s AND status = 'running'
                    """,
                    (
                        final_status.value,
                        len(batch.rows),
                        sum(anomaly.severity.value == "warning" for anomaly in result.anomalies)
                        + geometry_warning_count,
                        sum(anomaly.severity.value == "error" for anomaly in result.anomalies),
                        run_id,
                    ),
                )
            return final_status
        finally:
            connection.close()

    def mark_failed(self, reservation: ImportReservation) -> None:
        if reservation.run_id is None:
            raise ValueError("Reservation has no executable run")
        self._update_status(reservation.run_id, ImportStatus.FAILED)

    def _update_status(self, run_id: Any, status: ImportStatus) -> None:
        connection = self._connection_factory()
        try:
            with connection.transaction(), connection.cursor() as cursor:
                if status == ImportStatus.RUNNING:
                    cursor.execute(
                        """
                        UPDATE import_run SET status = 'running', started_at = now()
                        WHERE id = %s AND status = 'pending'
                        """,
                        (run_id,),
                    )
                elif status == ImportStatus.FAILED:
                    cursor.execute(
                        """
                        UPDATE import_run
                        SET status = 'failed', started_at = COALESCE(started_at, now()),
                            finished_at = now()
                        WHERE id = %s AND status IN ('pending', 'running')
                        """,
                        (run_id,),
                    )
                else:
                    raise ValueError(f"Unsupported direct status update: {status}")
        finally:
            connection.close()

    @staticmethod
    def _insert_staging(cursor: Cursor, run_id: Any, batch: StagingBatch) -> None:
        if batch.table == "staging_km_marker":
            cursor.executemany(
                """
                INSERT INTO staging_km_marker (
                    import_run_id, source_index, road_code, kilometer, raw_description,
                    original_geometry
                ) VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                """,
                ((run_id, *row) for row in batch.rows),
            )
        elif batch.table == "staging_mowing_polygon":
            cursor.executemany(
                """
                INSERT INTO staging_mowing_polygon (
                    import_run_id, source_index, equipment_class, kilometer_hint,
                    raw_attributes, original_geometry, inferred_latitude,
                    inferred_longitude, inferred_area_m2, inference_status
                ) VALUES (
                    %s, %s, %s, %s, %s::jsonb, ST_GeomFromText(%s, 4326),
                    %s, %s, %s, %s
                )
                """,
                ((run_id, *row) for row in batch.rows),
            )
        elif batch.table == "staging_vegetation_observation":
            cursor.executemany(
                """
                INSERT INTO staging_vegetation_observation (
                    import_run_id, version_label, sheet_name, reference_date,
                    item_code, description, station_meter, vegetation_class, source_cell
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                ((run_id, *row) for row in batch.rows),
            )
        elif batch.table != "none":
            raise ValueError(f"Unsupported staging table: {batch.table}")

    @staticmethod
    def _record_geometry_anomalies(cursor: Cursor, run_id: Any, table: str) -> int:
        if table != "staging_mowing_polygon":
            return 0
        cursor.execute(
            """
            SELECT count(*)
            FROM staging_mowing_polygon
            WHERE import_run_id = %s AND NOT ST_IsValid(original_geometry)
            """,
            (run_id,),
        )
        count_row = cursor.fetchone()
        invalid_count = int(count_row[0]) if count_row is not None else 0
        if invalid_count:
            cursor.execute(
                """
                INSERT INTO import_anomaly (
                    import_run_id, code, severity, source_record, message
                )
                SELECT import_run_id, 'invalid_geometry', 'warning',
                       'Placemark[' || source_index || ']',
                       ST_IsValidReason(original_geometry)
                FROM staging_mowing_polygon
                WHERE import_run_id = %s AND NOT ST_IsValid(original_geometry)
                """,
                (run_id,),
            )
        return invalid_count


def execute_import[RecordT](
    repository: PostgresImportRepository,
    plan: ImportPlan,
    parser: Callable[[Path], ParseResult[RecordT]],
) -> tuple[ImportReservation, ImportStatus | None]:
    """Reserve, parse, and persist one source while preserving failed attempts."""

    reservation = repository.reserve(plan)
    if reservation.decision in {
        ImportDecision.ALREADY_SUCCEEDED,
        ImportDecision.IN_PROGRESS,
    }:
        return reservation, reservation.previous_status
    repository.mark_running(reservation)
    try:
        result = parser(plan.source.path)
        return reservation, repository.persist_result(reservation, result)
    except Exception:
        repository.mark_failed(reservation)
        raise
