import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.work_orders import (
    PlannedInspectionPointResponse,
    PreparedInspectionOrderListMetadata,
    PreparedInspectionOrderListResponse,
    PreparedInspectionOrderRequest,
    PreparedInspectionOrderResponse,
    WorkOrderAlreadyExistsError,
    WorkOrderIdempotencyConflictError,
    WorkOrderPermissionError,
    WorkOrderPolicyUnavailableError,
    WorkOrderSourceDecisionError,
    WorkOrderSourceNotFoundError,
    get_prepared_inspection_order_repository,
)

USER_ID = UUID("30000000-0000-4000-8000-000000000001")
REVIEW_ID = UUID("30000000-0000-4000-8000-000000000002")
ORDER_ID = UUID("30000000-0000-4000-8000-000000000003")
ANALYSIS_ID = UUID("30000000-0000-4000-8000-000000000004")
ZONE_ID = UUID("30000000-0000-4000-8000-000000000005")
ACTOR = AuthenticatedUser(
    id=USER_ID,
    email="manager@example.test",
    display_name="MVP Manager",
)


def prepared_order() -> PreparedInspectionOrderResponse:
    return PreparedInspectionOrderResponse(
        work_order_id=ORDER_ID,
        source_review_id=REVIEW_ID,
        vegetation_analysis_id=ANALYSIS_ID,
        segment_zone_id=ZONE_ID,
        road_code="SP021",
        segment_index=195,
        zone_type="left",
        order_type="inspection",
        status="prepared",
        version=1,
        planning_rationale="Low-confidence result requires field inspection",
        creation_policy_version="prepared-inspection-order-v1",
        policy_data_status="prepared",
        order_data_status="prepared",
        source_axis_data_status="estimated",
        source_segment_data_status="estimated",
        source_zone_data_status="prepared",
        created_at=datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
        planned_points=[
            PlannedInspectionPointResponse(
                planned_point_id=UUID(f"30000000-0000-4000-8000-{sequence:012d}"),
                sequence=sequence,
                position_fraction=fraction,
                longitude=-46.8 + sequence / 1000,
                latitude=-23.5 + sequence / 1000,
                planning_method="segment_centerline_fraction",
                data_status="estimated",
            )
            for sequence, fraction in enumerate((1 / 6, 0.5, 5 / 6), start=1)
        ],
    )


class FakePreparedInspectionOrderRepository:
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def create(
        self,
        *,
        actor: AuthenticatedUser,
        idempotency_key: str,
        request: PreparedInspectionOrderRequest,
    ) -> PreparedInspectionOrderResponse:
        if self.failure is not None:
            raise self.failure
        assert actor == ACTOR
        assert idempotency_key == "inspection-order-attempt-0001"
        assert request.source_review_id == REVIEW_ID
        assert request.planning_rationale == "Low-confidence result requires field inspection"
        return prepared_order()

    async def list_for_user(
        self,
        *,
        actor: AuthenticatedUser,
        limit: int,
    ) -> PreparedInspectionOrderListResponse:
        assert actor == ACTOR
        assert limit == 20
        return PreparedInspectionOrderListResponse(
            items=[prepared_order()],
            metadata=PreparedInspectionOrderListMetadata(
                result_count=1,
                limit=limit,
                warning="Prepared inspection orders are not field-execution authorization.",
            ),
        )


def request_with_overrides(
    *,
    method: str = "POST",
    payload: dict | None = None,
    failure: type[Exception] | None = None,
):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_repository() -> FakePreparedInspectionOrderRepository:
        return FakePreparedInspectionOrderRepository(failure)

    async def request():
        app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_inspection_order_repository] = fake_repository
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                if method == "GET":
                    return await client.get("/v1/work-orders?limit=20")
                return await client.post(
                    "/v1/work-orders",
                    headers={"Idempotency-Key": "inspection-order-attempt-0001"},
                    json=payload,
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_create_prepared_inspection_order_preserves_all_safety_gates() -> None:
    response = request_with_overrides(
        payload={
            "source_review_id": str(REVIEW_ID),
            "planning_rationale": "  Low-confidence result requires field inspection  ",
        }
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "prepared"
    assert payload["order_type"] == "inspection"
    assert payload["authorizes_field_work"] is False
    assert payload["eligible_for_field_execution"] is False
    assert payload["eligible_for_official_reporting"] is False
    assert [point["sequence"] for point in payload["planned_points"]] == [1, 2, 3]
    assert all(
        point["eligible_for_field_execution"] is False
        for point in payload["planned_points"]
    )


def test_create_order_body_cannot_supply_actor_or_execution_authorization() -> None:
    response = request_with_overrides(
        payload={
            "source_review_id": str(REVIEW_ID),
            "planning_rationale": "Low-confidence result requires field inspection",
            "created_by_user_id": str(UUID(int=1)),
            "authorizes_field_work": True,
        }
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (WorkOrderSourceNotFoundError, 404),
        (WorkOrderSourceDecisionError, 409),
        (WorkOrderPermissionError, 403),
        (WorkOrderPolicyUnavailableError, 503),
        (WorkOrderIdempotencyConflictError, 409),
        (WorkOrderAlreadyExistsError, 409),
    ],
)
def test_order_domain_failures_have_stable_http_statuses(
    failure: type[Exception], expected_status: int
) -> None:
    response = request_with_overrides(
        payload={
            "source_review_id": str(REVIEW_ID),
            "planning_rationale": "Low-confidence result requires field inspection",
        },
        failure=failure,
    )

    assert response.status_code == expected_status


def test_order_list_is_scoped_to_the_authenticated_user() -> None:
    response = request_with_overrides(method="GET")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["result_count"] == 1
    assert payload["items"][0]["work_order_id"] == str(ORDER_ID)
    assert "created_by" not in response.text


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_work_order_endpoints_require_bearer_authentication(method: str) -> None:
    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            if method == "GET":
                return await client.get("/v1/work-orders")
            return await client.post(
                "/v1/work-orders",
                headers={"Idempotency-Key": "inspection-order-attempt-0001"},
                json={
                    "source_review_id": str(REVIEW_ID),
                    "planning_rationale": "Inspection required",
                },
            )

    response = asyncio.run(request())

    assert response.status_code == 401
