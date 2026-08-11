import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mowing_readiness import (
    PreparedMowingReadinessRequest,
    PreparedMowingReadinessResponse,
    ReadinessIdempotencyConflictError,
    ReadinessOrderNotFoundError,
    ReadinessPermissionError,
    ReadinessPolicyUnavailableError,
    ReadinessSourceError,
    ReadinessSupersessionError,
    get_prepared_mowing_readiness_repository,
)

ACTOR = AuthenticatedUser(
    id=UUID("72000000-0000-4000-8000-000000000001"),
    email="manager@example.test", display_name="Prepared Manager",
)
ORDER_ID = UUID("72000000-0000-4000-8000-000000000002")
PLAN_ID = UUID("72000000-0000-4000-8000-000000000003")
ASSESSMENT_ID = UUID("72000000-0000-4000-8000-000000000004")


class FakeReadinessWriter:
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def create(self, **values) -> PreparedMowingReadinessResponse:
        if self.failure:
            raise self.failure
        assert values["mowing_order_id"] == ORDER_ID
        assert values["actor"] == ACTOR
        request: PreparedMowingReadinessRequest = values["request"]
        return PreparedMowingReadinessResponse(
            readiness_assessment_id=ASSESSMENT_ID, mowing_order_id=ORDER_ID,
            resource_plan_id=request.resource_plan_id,
            weather_result=request.weather_result,
            weather_source_reference=request.weather_source_reference,
            safety_result=request.safety_result,
            safety_source_reference=request.safety_source_reference,
            assessment_rationale=request.assessment_rationale,
            supersedes_assessment_id=request.supersedes_assessment_id,
            policy_version="prepared-mowing-readiness-v1",
            validation_status="prepared_manual_pending_validation",
            data_status="prepared", requires_operational_approval=True,
            assessed_at=datetime(2026, 8, 11, 21, tzinfo=UTC),
        )


def request(*, failure=None, authenticated=True, payload=None):
    async def fake_actor(): return ACTOR
    async def fake_writer(): return FakeReadinessWriter(failure)

    async def execute():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_mowing_readiness_repository] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/prepared-mowing-orders/{ORDER_ID}/readiness-assessments",
                    headers={"Idempotency-Key": "readiness-attempt-0001"},
                    json=payload or {
                        "resource_plan_id": str(PLAN_ID),
                        "weather_result": "clear",
                        "weather_source_reference": "Consulta manual declarada",
                        "safety_result": "inconclusive",
                        "safety_source_reference": "Checklist ainda incompleto",
                        "assessment_rationale": "Registrar avaliação preparada sem liberar campo",
                    },
                )
        finally:
            app.dependency_overrides.clear()
    return asyncio.run(execute())


def test_clear_weather_still_never_authorizes_execution() -> None:
    response = request()
    assert response.status_code == 200
    payload = response.json()
    assert payload["weather_result"] == "clear"
    assert payload["validation_status"] == "prepared_manual_pending_validation"
    assert payload["requires_operational_approval"] is True
    assert payload["authorizes_field_work"] is False
    assert payload["eligible_for_field_execution"] is False
    assert payload["eligible_for_official_reporting"] is False


def test_readiness_forbids_promotion_fields_and_requires_sources() -> None:
    assert request(payload={
        "resource_plan_id": str(PLAN_ID), "weather_result": "clear",
        "weather_source_reference": "", "safety_result": "clear",
        "safety_source_reference": "Checklist manual",
        "assessment_rationale": "Avaliar", "authorizes_field_work": True,
    }).status_code == 422


@pytest.mark.parametrize(("failure", "status"), [
    (ReadinessOrderNotFoundError, 404), (ReadinessSourceError, 409),
    (ReadinessPermissionError, 403), (ReadinessPolicyUnavailableError, 503),
    (ReadinessSupersessionError, 409), (ReadinessIdempotencyConflictError, 409),
])
def test_readiness_failures_have_stable_statuses(failure, status) -> None:
    assert request(failure=failure).status_code == status


def test_readiness_requires_authentication() -> None:
    assert request(authenticated=False).status_code == 401
