from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError

import pytest
from scripts.verify_mvp_stack import SmokeCheckError, run_checks


class FakeResponse:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self.body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _success_opener(request: object, *, timeout: float) -> FakeResponse:
    del timeout
    url = request.full_url  # type: ignore[attr-defined]
    if url.endswith("/health"):
        return FakeResponse(
            200,
            json.dumps(
                {
                    "status": "ok",
                    "checks": {
                        "database": {"status": "ok", "required": True},
                        "object_storage": {"status": "ok", "required": True},
                        "queue": {"status": "not_configured", "required": False},
                    },
                }
            ).encode(),
        )
    if url.endswith("/satellite-observations") or url.endswith("/v1/recommendations"):
        return FakeResponse(200, b'{"items":[],"metadata":{"result_count":0}}')
    if url.startswith("http://dashboard.test"):
        return FakeResponse(200, b"<html></html>")
    raise HTTPError(url, 401, "Unauthorized", {}, io.BytesIO(b'{"detail":"unauthorized"}'))


def test_run_checks_covers_fresh_stack_contracts() -> None:
    count = run_checks(
        api_base="http://api.test",
        dashboard_base="http://dashboard.test",
        expect_empty=True,
        opener=_success_opener,
    )

    assert count == 25


def test_run_checks_rejects_unprotected_authenticated_route() -> None:
    def opener(request: object, *, timeout: float) -> FakeResponse:
        if request.full_url.endswith("/v1/auth/me"):  # type: ignore[attr-defined]
            return FakeResponse(200, b'{"id":"unexpected"}')
        return _success_opener(request, timeout=timeout)

    with pytest.raises(SmokeCheckError, match="current user authentication returned HTTP 200"):
        run_checks(
            api_base="http://api.test",
            dashboard_base="http://dashboard.test",
            opener=opener,
        )


def test_run_checks_rejects_invalid_health_payload() -> None:
    def opener(request: object, *, timeout: float) -> FakeResponse:
        if request.full_url.endswith("/health"):  # type: ignore[attr-defined]
            return FakeResponse(200, json.dumps({"status": "degraded"}).encode())
        return _success_opener(request, timeout=timeout)

    with pytest.raises(SmokeCheckError, match="health JSON status is not 'ok'"):
        run_checks(
            api_base="http://api.test",
            dashboard_base="http://dashboard.test",
            opener=opener,
        )


def test_run_checks_rejects_unverified_health_dependency() -> None:
    def opener(request: object, *, timeout: float) -> FakeResponse:
        if request.full_url.endswith("/health"):  # type: ignore[attr-defined]
            return FakeResponse(
                200,
                json.dumps(
                    {
                        "status": "ok",
                        "checks": {
                            "database": {"status": "ok", "required": True},
                            "object_storage": {"status": "unknown", "required": True},
                            "queue": {"status": "not_configured", "required": False},
                        },
                    }
                ).encode(),
            )
        return _success_opener(request, timeout=timeout)

    with pytest.raises(SmokeCheckError, match="invalid object_storage readiness"):
        run_checks(
            api_base="http://api.test",
            dashboard_base="http://dashboard.test",
            opener=opener,
        )


def test_run_checks_reports_connection_failures() -> None:
    def opener(request: object, *, timeout: float) -> FakeResponse:
        del request, timeout
        raise URLError("connection refused")

    with pytest.raises(SmokeCheckError, match=r"cannot reach http://api\.test/health"):
        run_checks(
            api_base="http://api.test",
            dashboard_base="http://dashboard.test",
            opener=opener,
        )
