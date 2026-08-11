import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mowing_planning_approvals import (
    PlanningApprovalDecisionError,
    PlanningApprovalIdempotencyConflictError,
    PlanningApprovalOrderNotFoundError,
    PlanningApprovalPermissionError,
    PlanningApprovalPolicyUnavailableError,
    PlanningApprovalSourceError,
    PlanningApprovalSupersessionError,
    PreparedMowingPlanningApprovalRequest,
    PreparedMowingPlanningApprovalResponse,
    get_prepared_mowing_planning_approval_repository,
)

ACTOR = AuthenticatedUser(
    id=UUID("73000000-0000-4000-8000-000000000001"),
    email="manager@example.test", display_name="Prepared Manager",
)
ORDER_ID = UUID("73000000-0000-4000-8000-000000000002")
ASSESSMENT_ID = UUID("73000000-0000-4000-8000-000000000003")
APPROVAL_ID = UUID("73000000-0000-4000-8000-000000000004")


class FakeApprovalWriter:
    def __init__(self, failure=None):
        self.failure = failure

    async def create(self, **values):
        if self.failure:
            raise self.failure
        request: PreparedMowingPlanningApprovalRequest = values["request"]
        return PreparedMowingPlanningApprovalResponse(
            planning_approval_id=APPROVAL_ID, mowing_order_id=ORDER_ID,
            readiness_assessment_id=request.readiness_assessment_id,
            decision=request.decision, decision_rationale=request.decision_rationale,
            supersedes_approval_id=request.supersedes_approval_id,
            policy_version="prepared-mowing-planning-approval-v1",
            approval_effect="planning_only_no_execution_authorization",
            dual_approval_requirement_status="pending_official_policy_validation",
            operational_approval_satisfied=False, data_status="prepared",
            decided_at=datetime(2026, 8, 11, 22, tzinfo=UTC),
        )


def request(*, failure=None, authenticated=True, payload=None):
    async def fake_actor():
        return ACTOR

    async def fake_writer():
        return FakeApprovalWriter(failure)

    async def execute():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_mowing_planning_approval_repository] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/prepared-mowing-orders/{ORDER_ID}/planning-approvals",
                    headers={"Idempotency-Key": "planning-approval-0001"},
                    json=payload or {
                        "readiness_assessment_id": str(ASSESSMENT_ID),
                        "decision": "approved_for_planning",
                        "decision_rationale": "Aprovar somente o cenário preparado",
                    },
                )
        finally:
            app.dependency_overrides.clear()
    return asyncio.run(execute())


def test_positive_planning_decision_never_satisfies_operational_approval() -> None:
    response = request()
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "approved_for_planning"
    assert payload["approval_effect"] == "planning_only_no_execution_authorization"
    assert payload["dual_approval_requirement_status"] == "pending_official_policy_validation"
    assert payload["operational_approval_satisfied"] is False
    assert payload["authorizes_field_work"] is False
    assert payload["eligible_for_field_execution"] is False


def test_approval_forbids_operational_promotion_fields() -> None:
    assert request(payload={
        "readiness_assessment_id": str(ASSESSMENT_ID),
        "decision": "approved_for_planning", "decision_rationale": "Planejamento",
        "operational_approval_satisfied": True, "authorizes_field_work": True,
    }).status_code == 422


@pytest.mark.parametrize(("failure", "status"), [
    (PlanningApprovalOrderNotFoundError, 404), (PlanningApprovalSourceError, 409),
    (PlanningApprovalDecisionError, 409), (PlanningApprovalPermissionError, 403),
    (PlanningApprovalPolicyUnavailableError, 503),
    (PlanningApprovalSupersessionError, 409),
    (PlanningApprovalIdempotencyConflictError, 409),
])
def test_planning_approval_failures_have_stable_statuses(failure, status) -> None:
    assert request(failure=failure).status_code == status


def test_planning_approval_requires_authentication() -> None:
    assert request(authenticated=False).status_code == 401
