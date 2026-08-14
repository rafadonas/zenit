import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from zenit_api import health as health_module
from zenit_api.config import Settings
from zenit_api.health import HealthSnapshot, RuntimeHealthProbe, get_health_probe
from zenit_api.main import app


class FakeHealthProbe:
    def __init__(self, snapshot: HealthSnapshot) -> None:
        self._snapshot = snapshot

    async def check(self) -> HealthSnapshot:
        return self._snapshot


def _request_health(snapshot: HealthSnapshot, correlation_id: str | None = None):
    async def fake_probe() -> FakeHealthProbe:
        return FakeHealthProbe(snapshot)

    async def request_health():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-Correlation-ID": correlation_id} if correlation_id else None
            return await client.get("/health", headers=headers)

    app.dependency_overrides[get_health_probe] = fake_probe
    try:
        return asyncio.run(request_health())
    finally:
        app.dependency_overrides.clear()


def test_health_returns_service_and_dependency_readiness() -> None:
    response = _request_health(
        HealthSnapshot(database_ready=True, object_storage_ready=True)
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "zenit",
        "version": "0.1.0",
        "environment": "development",
        "checks": {
            "database": {"status": "ok", "required": True},
            "object_storage": {"status": "ok", "required": True},
            "queue": {"status": "not_configured", "required": False},
        },
    }


def test_health_fails_closed_without_leaking_dependency_details() -> None:
    correlation_id = "20000000-0000-4000-8000-000000000004"
    response = _request_health(
        HealthSnapshot(database_ready=False, object_storage_ready=True),
        correlation_id,
    )

    assert response.status_code == 503
    assert response.json() == {
        "code": "service_unavailable",
        "message": "Required health dependency is unavailable",
        "details": None,
        "correlation_id": correlation_id,
    }


def test_runtime_probe_fails_closed_when_a_dependency_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def database_ready(_: Settings) -> bool:
        return True

    async def storage_failure(_: Settings) -> bool:
        raise RuntimeError("private storage failure")

    monkeypatch.setattr(health_module, "_database_ready", database_ready)
    monkeypatch.setattr(health_module, "_object_storage_ready", storage_failure)

    snapshot = asyncio.run(RuntimeHealthProbe(Settings()).check())

    assert snapshot.database_ready is True
    assert snapshot.object_storage_ready is False
    assert snapshot.unavailable_dependencies == ("object_storage",)


def test_health_probe_timeout_is_bounded() -> None:
    with pytest.raises(ValidationError, match="health_probe_timeout_seconds"):
        Settings(health_probe_timeout_seconds=0.05)
