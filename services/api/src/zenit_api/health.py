"""Dependency-aware API readiness reporting."""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass
from typing import Annotated, Literal, Protocol
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from zenit_api.config import Settings, get_settings

logger = logging.getLogger(__name__)


class HealthDependencyResponse(BaseModel):
    status: Literal["ok", "not_configured"]
    required: bool


class HealthChecksResponse(BaseModel):
    database: HealthDependencyResponse
    object_storage: HealthDependencyResponse
    queue: HealthDependencyResponse


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    environment: str
    checks: HealthChecksResponse


@dataclass(frozen=True)
class HealthSnapshot:
    database_ready: bool
    object_storage_ready: bool

    @property
    def unavailable_dependencies(self) -> tuple[str, ...]:
        unavailable: list[str] = []
        if not self.database_ready:
            unavailable.append("database")
        if not self.object_storage_ready:
            unavailable.append("object_storage")
        return tuple(unavailable)


class HealthProbe(Protocol):
    async def check(self) -> HealthSnapshot: ...


async def _database_ready(settings: Settings) -> bool:
    database_url = settings.database_url.replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )
    connect_timeout = max(1, math.ceil(settings.health_probe_timeout_seconds))
    async with asyncio.timeout(settings.health_probe_timeout_seconds):
        connection = await psycopg.AsyncConnection.connect(
            database_url,
            connect_timeout=connect_timeout,
        )
        async with connection, connection.cursor() as cursor:
            await cursor.execute("SELECT 1")
            return await cursor.fetchone() == (1,)


def _request_object_storage_health(settings: Settings) -> bool:
    health_url = f"{settings.object_storage_endpoint.rstrip('/')}/minio/health/ready"
    request = UrlRequest(health_url, method="GET")
    with urlopen(request, timeout=settings.health_probe_timeout_seconds) as response:
        return response.status == 200


async def _object_storage_ready(settings: Settings) -> bool:
    return await asyncio.to_thread(_request_object_storage_health, settings)


class RuntimeHealthProbe:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def check(self) -> HealthSnapshot:
        database_result, object_storage_result = await asyncio.gather(
            _database_ready(self._settings),
            _object_storage_ready(self._settings),
            return_exceptions=True,
        )
        return HealthSnapshot(
            database_ready=database_result is True,
            object_storage_ready=object_storage_result is True,
        )


async def get_health_settings() -> Settings:
    return get_settings()


async def get_health_probe(
    settings: Annotated[Settings, Depends(get_health_settings)],
) -> HealthProbe:
    return RuntimeHealthProbe(settings)


router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(
    request: Request,
    settings: Annotated[Settings, Depends(get_health_settings)],
    probe: Annotated[HealthProbe, Depends(get_health_probe)],
) -> HealthResponse:
    snapshot = await probe.check()
    unavailable = snapshot.unavailable_dependencies
    if unavailable:
        logger.warning(
            "Required health dependencies unavailable",
            extra={
                "correlation_id": str(request.state.correlation_id),
                "dependencies": ",".join(unavailable),
            },
        )
        raise HTTPException(status_code=503, detail="Required health dependency is unavailable")

    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        checks=HealthChecksResponse(
            database=HealthDependencyResponse(status="ok", required=True),
            object_storage=HealthDependencyResponse(status="ok", required=True),
            queue=HealthDependencyResponse(status="not_configured", required=False),
        ),
    )
