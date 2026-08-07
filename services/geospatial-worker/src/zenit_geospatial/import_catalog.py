from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


class ImportDecision(StrEnum):
    PLANNED = "planned"
    ALREADY_SUCCEEDED = "already_succeeded"
    RETRY_FAILED = "retry_failed"
    IN_PROGRESS = "in_progress"


class ImportStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    path: Path
    sha256: str
    size_bytes: int
    detected_format: str


@dataclass(frozen=True, slots=True)
class ImportIdentity:
    source_sha256: str
    parser_name: str
    parser_version: str
    parameters: dict[str, Any]
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ImportPlan:
    source: SourceIdentity
    identity: ImportIdentity
    decision: ImportDecision
    previous_status: ImportStatus | None = None


class ImportCatalog(Protocol):
    def status_for(self, idempotency_key: str) -> ImportStatus | None: ...


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_parameters(parameters: dict[str, Any] | None) -> str:
    return json.dumps(parameters or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def make_idempotency_key(
    source_sha256: str,
    parser_name: str,
    parser_version: str,
    parameters: dict[str, Any] | None = None,
) -> str:
    identity = "\n".join(
        (source_sha256, parser_name, parser_version, canonical_parameters(parameters))
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def identify_source(path: Path, detected_format: str) -> SourceIdentity:
    return SourceIdentity(
        path=path,
        sha256=file_sha256(path),
        size_bytes=path.stat().st_size,
        detected_format=detected_format,
    )


def plan_import(
    source: SourceIdentity,
    parser_name: str,
    parser_version: str,
    catalog: ImportCatalog,
    parameters: dict[str, Any] | None = None,
) -> ImportPlan:
    normalized_parameters = parameters or {}
    key = make_idempotency_key(
        source.sha256,
        parser_name,
        parser_version,
        normalized_parameters,
    )
    previous_status = catalog.status_for(key)
    if previous_status == ImportStatus.SUCCEEDED:
        decision = ImportDecision.ALREADY_SUCCEEDED
    elif previous_status in {ImportStatus.PENDING, ImportStatus.RUNNING}:
        decision = ImportDecision.IN_PROGRESS
    elif previous_status in {ImportStatus.FAILED, ImportStatus.REJECTED}:
        decision = ImportDecision.RETRY_FAILED
    else:
        decision = ImportDecision.PLANNED
    return ImportPlan(
        source=source,
        identity=ImportIdentity(
            source_sha256=source.sha256,
            parser_name=parser_name,
            parser_version=parser_version,
            parameters=normalized_parameters,
            idempotency_key=key,
        ),
        decision=decision,
        previous_status=previous_status,
    )


class InMemoryImportCatalog:
    """Test adapter; production persistence belongs in the Postgres adapter."""

    def __init__(self) -> None:
        self._statuses: dict[str, ImportStatus] = {}

    def status_for(self, idempotency_key: str) -> ImportStatus | None:
        return self._statuses.get(idempotency_key)

    def set_status(self, idempotency_key: str, status: ImportStatus) -> None:
        self._statuses[idempotency_key] = status
