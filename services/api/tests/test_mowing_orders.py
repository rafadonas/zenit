import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mowing_orders import (
    MowingOrderAlreadyExistsError,
    MowingOrderIdempotencyConflictError,
    MowingOrderPermissionError,
    MowingOrderPolicyUnavailableError,
    MowingOrderSourceDecisionError,
    MowingOrderSourceNotFoundError,
    PreparedMowingOrderCollection,
    PreparedMowingOrderRequest,
    PreparedMowingOrderResponse,
    get_prepared_mowing_order_repository,
)

ACTOR = AuthenticatedUser(
    id=UUID("70000000-0000-4000-8000-000000000001"),
    email="manager@example.test",
    display_name="Prepared Manager",
)
REVIEW_ID = UUID("70000000-0000-4000-8000-000000000002")
PROPOSAL_ID = UUID("70000000-0000-4000-8000-000000000003")
INSPECTION_ORDER_ID = UUID("70000000-0000-4000-8000-000000000004")
MOWING_ORDER_ID = UUID("70000000-0000-4000-8000-000000000005")


def mowing_order() -> PreparedMowingOrderResponse:
    return PreparedMowingOrderResponse(
        mowing_order_id=MOWING_ORDER_ID,
        proposal_id=PROPOSAL_ID,
        source_review_id=REVIEW_ID,
        source_inspection_work_order_id=INSPECTION_ORDER_ID,
        road_code="SP-021",
        segment_index=195,
        zone_type="special",
        creation_recommendation="mowing_review",
        source_review_state="effective",
        order_type="mowing",
        status="prepared",
        version=1,
        planning_rationale="Preparar planejamento sem liberar execução",
        creation_policy_version="prepared-mowing-order-v1",
        data_status="prepared",
        location_status="simulated",
        source_evidence_status="prepared_reviewed_non_operational",
        team_assignment_status="unassigned",
        equipment_assignment_status="unassigned",
        weather_check_status="pending",
        safety_check_status="pending",
        requires_operational_approval=True,
        created_at=datetime(2026, 8, 11, 19, tzinfo=UTC),
    )


class FakeMowingOrderRepository:
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def create(self, **values) -> PreparedMowingOrderResponse:
        if self.failure:
            raise self.failure
        assert values["actor"] == ACTOR
        assert values["idempotency_key"] == "mowing-order-attempt-0001"
        request: PreparedMowingOrderRequest = values["request"]
        assert request.source_review_id == REVIEW_ID
        assert request.planning_rationale == "Preparar planejamento sem liberar execução"
        return mowing_order()

    async def list_for_actor(self, **values) -> PreparedMowingOrderCollection:
        assert values == {"actor": ACTOR, "limit": 9}
        return PreparedMowingOrderCollection(
            items=[mowing_order()], result_count=1, limit=9, truncated=False
        )


def request(
    *, method: str = "POST", failure: type[Exception] | None = None,
    authenticated: bool = True, payload: dict | None = None,
):
    async def fake_actor():
        return ACTOR

    async def fake_repository():
        return FakeMowingOrderRepository(failure)

    async def execute():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_mowing_order_repository] = fake_repository
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                if method == "GET":
                    return await client.get("/v1/prepared-mowing-orders?limit=9")
                return await client.post(
                    "/v1/prepared-mowing-orders",
                    headers={"Idempotency-Key": "mowing-order-attempt-0001"},
                    json=payload or {
                        "source_review_id": str(REVIEW_ID),
                        "planning_rationale": "  Preparar planejamento sem liberar execução  ",
                    },
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(execute())


def test_create_mowing_order_preserves_every_execution_block() -> None:
    response = request()
    assert response.status_code == 200
    payload = response.json()
    assert payload["creation_recommendation"] == "mowing_review"
    assert payload["source_review_state"] == "effective"
    assert payload["status"] == "prepared"
    assert payload["team_assignment_status"] == "unassigned"
    assert payload["equipment_assignment_status"] == "unassigned"
    assert payload["weather_check_status"] == "pending"
    assert payload["safety_check_status"] == "pending"
    assert payload["requires_operational_approval"] is True
    assert payload["authorizes_field_work"] is False
    assert payload["eligible_for_field_execution"] is False
    assert payload["eligible_for_official_reporting"] is False


def test_mowing_order_forbids_actor_and_authorization_fields() -> None:
    response = request(payload={
        "source_review_id": str(REVIEW_ID),
        "planning_rationale": "Preparar planejamento sem liberar execução",
        "created_by_user_id": str(ACTOR.id),
        "authorizes_field_work": True,
    })
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("failure", "status"),
    [
        (MowingOrderSourceNotFoundError, 404),
        (MowingOrderSourceDecisionError, 409),
        (MowingOrderPermissionError, 403),
        (MowingOrderPolicyUnavailableError, 503),
        (MowingOrderIdempotencyConflictError, 409),
        (MowingOrderAlreadyExistsError, 409),
    ],
)
def test_mowing_order_failures_have_stable_statuses(
    failure: type[Exception], status: int
) -> None:
    assert request(failure=failure).status_code == status


def test_mowing_order_list_is_actor_scoped_and_hides_creator() -> None:
    response = request(method="GET")
    assert response.status_code == 200
    assert response.json()["items"][0]["mowing_order_id"] == str(MOWING_ORDER_ID)
    assert "created_by" not in response.text


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_mowing_order_endpoints_require_authentication(method: str) -> None:
    assert request(method=method, authenticated=False).status_code == 401
