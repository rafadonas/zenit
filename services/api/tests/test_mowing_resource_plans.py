import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mowing_resource_plans import (
    PreparedMowingResourcePlanRequest,
    PreparedMowingResourcePlanResponse,
    ResourcePlanIdempotencyConflictError,
    ResourcePlanOrderNotFoundError,
    ResourcePlanOrderObsoleteError,
    ResourcePlanPermissionError,
    ResourcePlanPolicyUnavailableError,
    ResourcePlanSupersessionError,
    get_prepared_mowing_resource_plan_repository,
)

ACTOR = AuthenticatedUser(
    id=UUID("71000000-0000-4000-8000-000000000001"),
    email="manager@example.test",
    display_name="Prepared Manager",
)
MOWING_ORDER_ID = UUID("71000000-0000-4000-8000-000000000002")
PLAN_ID = UUID("71000000-0000-4000-8000-000000000003")


class FakeResourcePlanWriter:
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def create(self, **values) -> PreparedMowingResourcePlanResponse:
        if self.failure:
            raise self.failure
        assert values["mowing_order_id"] == MOWING_ORDER_ID
        assert values["actor"] == ACTOR
        assert values["idempotency_key"] == "resource-plan-attempt-0001"
        request: PreparedMowingResourcePlanRequest = values["request"]
        assert request.team_reference == "Equipe candidata A"
        assert request.equipment_reference == "Equipamento candidato B"
        return PreparedMowingResourcePlanResponse(
            resource_plan_id=PLAN_ID,
            mowing_order_id=MOWING_ORDER_ID,
            team_reference=request.team_reference,
            equipment_reference=request.equipment_reference,
            planning_rationale=request.planning_rationale,
            supersedes_plan_id=request.supersedes_plan_id,
            policy_version="prepared-mowing-resource-plan-v1",
            resource_reference_status="prepared_placeholder_pending_validation",
            data_status="prepared",
            team_assignment_status="unassigned",
            equipment_assignment_status="unassigned",
            requires_operational_approval=True,
            created_at=datetime(2026, 8, 11, 20, tzinfo=UTC),
        )


def request(
    *, failure: type[Exception] | None = None, authenticated: bool = True,
    payload: dict | None = None,
):
    async def fake_actor():
        return ACTOR

    async def fake_writer():
        return FakeResourcePlanWriter(failure)

    async def execute():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_mowing_resource_plan_repository] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/prepared-mowing-orders/{MOWING_ORDER_ID}/resource-plans",
                    headers={"Idempotency-Key": "resource-plan-attempt-0001"},
                    json=payload or {
                        "team_reference": "  Equipe candidata A  ",
                        "equipment_reference": "  Equipamento candidato B  ",
                        "planning_rationale": "  Planejar recursos ainda não verificados  ",
                    },
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(execute())


def test_resource_plan_remains_unverified_unassigned_and_non_executable() -> None:
    response = request()
    assert response.status_code == 200
    payload = response.json()
    assert payload["resource_reference_status"] == "prepared_placeholder_pending_validation"
    assert payload["team_assignment_status"] == "unassigned"
    assert payload["equipment_assignment_status"] == "unassigned"
    assert payload["requires_operational_approval"] is True
    assert payload["authorizes_field_work"] is False
    assert payload["eligible_for_field_execution"] is False
    assert payload["eligible_for_official_reporting"] is False


def test_resource_plan_forbids_promotion_fields() -> None:
    response = request(payload={
        "team_reference": "Equipe candidata A",
        "equipment_reference": "Equipamento candidato B",
        "planning_rationale": "Planejar recursos ainda não verificados",
        "team_assignment_status": "assigned",
        "authorizes_field_work": True,
    })
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (ResourcePlanOrderNotFoundError, 404),
        (ResourcePlanOrderObsoleteError, 409),
        (ResourcePlanPermissionError, 403),
        (ResourcePlanPolicyUnavailableError, 503),
        (ResourcePlanSupersessionError, 409),
        (ResourcePlanIdempotencyConflictError, 409),
    ],
)
def test_resource_plan_failures_have_stable_statuses(
    failure: type[Exception], status: int
) -> None:
    assert request(failure=failure).status_code == status


def test_resource_plan_requires_authentication() -> None:
    assert request(authenticated=False).status_code == 401
