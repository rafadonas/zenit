#!/usr/bin/env python3
"""Verify the public and authentication boundaries of a running MVP stack."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REFERENCE_ID = "00000000-0000-4000-8000-000000000001"


class Response(Protocol):
    status: int

    def __enter__(self) -> Response: ...

    def __exit__(self, *args: object) -> None: ...

    def read(self) -> bytes: ...


Opener = Callable[..., Response]


class SmokeCheckError(RuntimeError):
    """Raised when a running service violates an MVP smoke contract."""


@dataclass(frozen=True)
class StatusCheck:
    name: str
    base: str
    path: str
    expected_status: int
    method: str = "GET"
    payload: dict[str, object] | None = None
    idempotency_key: str | None = None


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    idempotency_key: str | None = None,
    timeout: float = 5.0,
    opener: Opener | None = None,
) -> tuple[int, bytes]:
    headers: dict[str, str] = {}
    data = None
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode()
        headers["Content-Type"] = "application/json"
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    request = Request(url, data=data, headers=headers, method=method)
    open_request = opener or urlopen
    try:
        with open_request(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        raise SmokeCheckError(f"cannot reach {url}: {exc.reason}") from exc


def _decode_object(body: bytes, name: str) -> dict[str, object]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeCheckError(f"{name} did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise SmokeCheckError(f"{name} did not return a JSON object")
    return payload


def _expect_status(
    check: StatusCheck,
    *,
    timeout: float,
    opener: Opener | None,
) -> bytes:
    url = _url(check.base, check.path)
    status, body = _request(
        url,
        method=check.method,
        payload=check.payload,
        idempotency_key=check.idempotency_key,
        timeout=timeout,
        opener=opener,
    )
    if status != check.expected_status:
        raise SmokeCheckError(
            f"{check.name} returned HTTP {status}; expected {check.expected_status} ({url})"
        )
    print(f"PASS {check.name}: HTTP {status}")
    return body


def _protected_checks(api_base: str) -> tuple[StatusCheck, ...]:
    return (
        StatusCheck("current user authentication", api_base, "/v1/auth/me", 401),
        StatusCheck(
            "session logout authentication",
            api_base,
            "/v1/auth/logout",
            401,
            "POST",
        ),
        StatusCheck(
            "recommendation decision authentication",
            api_base,
            f"/v1/recommendations/{REFERENCE_ID}/decisions",
            401,
            "POST",
            {"decision": "accepted"},
            "smoke-recommendation-decision",
        ),
        StatusCheck("work order list authentication", api_base, "/v1/work-orders", 401),
        StatusCheck(
            "work order creation authentication",
            api_base,
            "/v1/work-orders",
            401,
            "POST",
            {
                "source_review_id": REFERENCE_ID,
                "planning_rationale": "MVP smoke authentication boundary",
            },
            "smoke-work-order",
        ),
        StatusCheck(
            "mobile registration authentication",
            api_base,
            "/v1/mobile/devices",
            401,
            "POST",
            {},
        ),
        StatusCheck(
            "mobile sync authentication", api_base, "/v1/sync/batch", 401, "POST", {}
        ),
        StatusCheck(
            "inspection summary export authentication",
            api_base,
            f"/v1/prepared-inspection-summaries/{REFERENCE_ID}/exports",
            401,
            "POST",
            {"export_purpose": "MVP smoke authentication boundary"},
            "smoke-inspection-export",
        ),
        StatusCheck(
            "post-inspection proposal creation authentication",
            api_base,
            f"/v1/prepared-inspection-summaries/{REFERENCE_ID}/post-inspection-proposal",
            401,
            "POST",
            {"creation_rationale": "MVP smoke authentication boundary"},
            "smoke-post-inspection-proposal",
        ),
        StatusCheck(
            "post-inspection proposal list authentication",
            api_base,
            "/v1/prepared-post-inspection-proposals",
            401,
        ),
        StatusCheck(
            "post-inspection review authentication",
            api_base,
            f"/v1/prepared-post-inspection-proposals/{REFERENCE_ID}/decisions",
            401,
            "POST",
            {"decision": "accepted"},
            "smoke-post-inspection-review",
        ),
        StatusCheck(
            "mowing order creation authentication",
            api_base,
            "/v1/prepared-mowing-orders",
            401,
            "POST",
            {
                "source_review_id": REFERENCE_ID,
                "planning_rationale": "MVP smoke authentication boundary",
            },
            "smoke-mowing-order",
        ),
        StatusCheck(
            "resource plan authentication",
            api_base,
            f"/v1/prepared-mowing-orders/{REFERENCE_ID}/resource-plans",
            401,
            "POST",
            {
                "team_reference": "candidate",
                "equipment_reference": "candidate",
                "planning_rationale": "MVP smoke authentication boundary",
            },
            "smoke-resource-plan",
        ),
        StatusCheck(
            "readiness assessment authentication",
            api_base,
            f"/v1/prepared-mowing-orders/{REFERENCE_ID}/readiness-assessments",
            401,
            "POST",
            {
                "resource_plan_id": REFERENCE_ID,
                "weather_result": "inconclusive",
                "weather_source_reference": "manual",
                "safety_result": "inconclusive",
                "safety_source_reference": "manual",
                "assessment_rationale": "MVP smoke authentication boundary",
            },
            "smoke-readiness-assessment",
        ),
        StatusCheck(
            "planning approval authentication",
            api_base,
            f"/v1/prepared-mowing-orders/{REFERENCE_ID}/planning-approvals",
            401,
            "POST",
            {
                "readiness_assessment_id": REFERENCE_ID,
                "decision": "rejected",
                "decision_rationale": "MVP smoke authentication boundary",
            },
            "smoke-planning-approval",
        ),
        StatusCheck(
            "post-service summary creation authentication",
            api_base,
            f"/v1/prepared-mowing-orders/{REFERENCE_ID}/post-service-summary",
            401,
            "POST",
            {"generation_rationale": "MVP smoke authentication boundary"},
            "smoke-post-service-summary",
        ),
        StatusCheck(
            "post-service summary list authentication",
            api_base,
            "/v1/prepared-mowing-post-service-summaries",
            401,
        ),
        StatusCheck(
            "post-service summary export authentication",
            api_base,
            f"/v1/prepared-mowing-post-service-summaries/{REFERENCE_ID}/exports",
            401,
            "POST",
            {"export_purpose": "MVP smoke authentication boundary"},
            "smoke-post-service-summary-export",
        ),
        StatusCheck(
            "post-service exception creation authentication",
            api_base,
            f"/v1/prepared-mowing-post-service-summaries/{REFERENCE_ID}/exceptions",
            401,
            "POST",
            {"creation_rationale": "MVP smoke authentication boundary"},
            "smoke-post-service-exception",
        ),
        StatusCheck(
            "post-service exception list authentication",
            api_base,
            "/v1/prepared-mowing-post-service-exceptions",
            401,
        ),
        StatusCheck(
            "post-service exception review authentication",
            api_base,
            f"/v1/prepared-mowing-post-service-exceptions/{REFERENCE_ID}/decisions",
            401,
            "POST",
            {"decision": "accepted"},
            "smoke-post-service-exception-review",
        ),
    )


def _verify_collection(body: bytes, name: str, *, expect_empty: bool) -> None:
    payload = _decode_object(body, name)
    items = payload.get("items")
    metadata = payload.get("metadata")
    if not isinstance(items, list) or not isinstance(metadata, dict):
        raise SmokeCheckError(f"{name} is missing collection items or metadata")
    result_count = metadata.get("result_count")
    if not isinstance(result_count, int) or result_count != len(items):
        raise SmokeCheckError(f"{name} has inconsistent metadata.result_count")
    if expect_empty and items:
        raise SmokeCheckError(f"{name} was expected to be empty in a fresh stack")


def _verify_health(body: bytes) -> None:
    payload = _decode_object(body, "API health")
    if payload.get("status") != "ok":
        raise SmokeCheckError("API health JSON status is not 'ok'")
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        raise SmokeCheckError("API health is missing dependency checks")

    expected = {
        "database": {"status": "ok", "required": True},
        "object_storage": {"status": "ok", "required": True},
        "queue": {"status": "not_configured", "required": False},
    }
    for dependency, expected_status in expected.items():
        if checks.get(dependency) != expected_status:
            raise SmokeCheckError(f"API health has invalid {dependency} readiness")


def _verify_dashboard_page(body: bytes, name: str, marker: str) -> None:
    try:
        document = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SmokeCheckError(f"{name} did not return UTF-8 HTML") from exc
    if "<html" not in document.lower():
        raise SmokeCheckError(f"{name} did not return an HTML document")
    if marker not in document:
        raise SmokeCheckError(f"{name} is missing its rendered page marker")


def run_checks(
    *,
    api_base: str,
    dashboard_base: str,
    expect_empty: bool = False,
    timeout: float = 5.0,
    opener: Opener | None = None,
) -> int:
    check_count = 0

    health = StatusCheck("API health", api_base, "/health", 200)
    health_body = _expect_status(health, timeout=timeout, opener=opener)
    _verify_health(health_body)
    check_count += 1

    collections = (
        StatusCheck(
            "satellite observation collection",
            api_base,
            f"/v1/segments/{REFERENCE_ID}/satellite-observations",
            200,
        ),
        StatusCheck("recommendation collection", api_base, "/v1/recommendations", 200),
    )
    for check in collections:
        body = _expect_status(check, timeout=timeout, opener=opener)
        _verify_collection(body, check.name, expect_empty=expect_empty)
        check_count += 1

    for check in _protected_checks(api_base):
        _expect_status(check, timeout=timeout, opener=opener)
        check_count += 1

    for check, marker in (
        (
            StatusCheck("dashboard", dashboard_base, "/", 200),
            'data-zenit-smoke-page="corridor"',
        ),
        (
            StatusCheck("dashboard login", dashboard_base, "/login", 200),
            'data-zenit-smoke-page="login"',
        ),
    ):
        body = _expect_status(check, timeout=timeout, opener=opener)
        _verify_dashboard_page(body, check.name, marker)
        check_count += 1

    return check_count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--dashboard-base", default="http://localhost:3000")
    parser.add_argument(
        "--expect-empty",
        action="store_true",
        help="require public collections to be empty, as expected in a fresh CI stack",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        count = run_checks(
            api_base=args.api_base,
            dashboard_base=args.dashboard_base,
            expect_empty=args.expect_empty,
            timeout=args.timeout,
        )
    except SmokeCheckError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"MVP stack smoke checks passed ({count} checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
