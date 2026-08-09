import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mobile_sync import (
    AcceptedSyncEventResponse,
    MobileDeviceNotRegisteredError,
    MobileDeviceOwnershipError,
    MobileDeviceRegistrationRequest,
    MobileDeviceRegistrationResponse,
    MobileDeviceRevokedError,
    MobileSyncBatchConflictError,
    MobileSyncBatchRequest,
    MobileSyncBatchResponse,
    MobileSyncCursorAheadError,
    MobileSyncEventRequest,
    PostgresMobileSyncRepository,
    RejectedSyncEventResponse,
    get_mobile_sync_repository,
)

USER_ID = UUID("40000000-0000-4000-8000-000000000001")
DEVICE_ID = UUID("40000000-0000-4000-8000-000000000002")
BATCH_ID = UUID("40000000-0000-4000-8000-000000000003")
EVENT_ID = UUID("40000000-0000-4000-8000-000000000004")
ORDER_ID = UUID("40000000-0000-4000-8000-000000000005")
POINT_ID = UUID("40000000-0000-4000-8000-000000000006")
ACTOR = AuthenticatedUser(
    id=USER_ID,
    email="field@example.test",
    display_name="Prepared Field User",
)


def measurement_event() -> dict:
    return {
        "event_id": str(EVENT_ID),
        "entity_type": "measurement",
        "operation": "create",
        "payload": {
            "work_order_id": str(ORDER_ID),
            "planned_point_id": str(POINT_ID),
            "phase": "inspection",
            "height_cm": 22.5,
            "captured_at": "2026-08-09T14:00:00-03:00",
            "data_status": "prepared",
            "eligible_for_official_reporting": False,
            "location_status": "not_collected",
            "photo_status": "not_collected",
        },
    }


def demo_order_event(operation: str) -> dict:
    payload = {
        "work_order_id": str(ORDER_ID),
        "occurred_at": "2026-08-09T14:00:00-03:00",
        "data_status": "simulated",
        "simulation_scope": "demo_only",
        "authorizes_field_work": False,
        "eligible_for_official_reporting": False,
        "location_status": "not_collected",
    }
    if operation == "start":
        payload.update(
            {
                "location_status": "simulated",
                "simulated_latitude": -23.5,
                "simulated_longitude": -46.7,
                "simulation_method": "prepared_point_demo_v1",
            }
        )
    return {
        "event_id": str(EVENT_ID),
        "entity_type": "work_order",
        "operation": operation,
        "payload": payload,
    }


def photo_manifest_event() -> dict:
    return {
        "event_id": str(EVENT_ID),
        "entity_type": "photo",
        "operation": "prepare",
        "payload": {
            "photo_id": "40000000-0000-4000-8000-000000000007",
            "work_order_id": str(ORDER_ID),
            "planned_point_id": str(POINT_ID),
            "phase": "inspection",
            "captured_at": "2026-08-09T14:00:00-03:00",
            "checksum_sha256": "a" * 64,
            "byte_size": 1024,
            "media_type": "image/jpeg",
            "content_status": "not_uploaded",
            "ruler_status": "not_validated",
            "location_status": "not_collected",
            "data_status": "prepared",
            "eligible_for_official_reporting": False,
        },
    }


class FakeMobileSyncRepository:
    def __init__(self, failure: type[Exception] | None = None) -> None:
        self.failure = failure

    async def register_device(
        self,
        *,
        actor: AuthenticatedUser,
        request: MobileDeviceRegistrationRequest,
    ) -> MobileDeviceRegistrationResponse:
        if self.failure is not None:
            raise self.failure
        assert actor == ACTOR
        assert request.device_id == DEVICE_ID
        return MobileDeviceRegistrationResponse(
            device_id=request.device_id,
            platform="android",
            registered_app_version=request.app_version,
            registered_at=datetime(2026, 8, 9, 17, 0, tzinfo=UTC),
        )

    async def sync_batch(
        self,
        *,
        actor: AuthenticatedUser,
        request: MobileSyncBatchRequest,
    ) -> MobileSyncBatchResponse:
        if self.failure is not None:
            raise self.failure
        assert actor == ACTOR
        event = request.events[0]
        if (
            event.entity_type != "measurement"
            and event.operation not in {"confirm", "start", "finish"}
            and not (event.entity_type == "photo" and event.operation == "prepare")
        ):
            return MobileSyncBatchResponse(
                batch_id=request.batch_id,
                accepted=[],
                rejected=[
                    RejectedSyncEventResponse(
                        event_id=event.event_id,
                        code="unsupported_event",
                        message="event type is not supported",
                    )
                ],
                conflicts=[],
                next_sync_cursor=1,
            )
        return MobileSyncBatchResponse(
            batch_id=request.batch_id,
            accepted=[AcceptedSyncEventResponse(event_id=event.event_id)],
            rejected=[],
            conflicts=[],
            next_sync_cursor=1,
        )


def request_with_overrides(
    *,
    endpoint: str,
    payload: dict,
    failure: type[Exception] | None = None,
):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_repository() -> FakeMobileSyncRepository:
        return FakeMobileSyncRepository(failure)

    async def request():
        app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_mobile_sync_repository] = fake_repository
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(endpoint, json=payload)
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_register_device_is_authenticated_prepared_and_non_operational() -> None:
    response = request_with_overrides(
        endpoint="/v1/mobile/devices",
        payload={
            "device_id": str(DEVICE_ID),
            "platform": "android",
            "app_version": " 1.0.0+1 ",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["registration_status"] == "active"
    assert payload["data_status"] == "prepared"
    assert payload["authorizes_field_work"] is False
    assert payload["registered_app_version"] == "1.0.0+1"


def test_sync_accepts_only_explicitly_prepared_non_official_measurement() -> None:
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [measurement_event()],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] == [{"event_id": str(EVENT_ID), "persisted": True}]
    assert payload["rejected"] == []
    assert payload["conflicts"] == []
    assert payload["authorizes_field_work"] is False
    assert payload["eligible_for_official_reporting"] is False


def test_sync_records_unknown_work_order_operation_as_rejected() -> None:
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [
                {
                    "event_id": str(EVENT_ID),
                    "entity_type": "work_order",
                    "operation": "pause",
                    "payload": {"work_order_id": str(ORDER_ID)},
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["rejected"][0]["code"] == "unsupported_event"


@pytest.mark.parametrize("operation", ["confirm", "start", "finish"])
def test_sync_contract_accepts_explicit_demo_order_events(operation: str) -> None:
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [demo_order_event(operation)],
        },
    )

    assert response.status_code == 200
    assert response.json()["accepted"] == [{"event_id": str(EVENT_ID), "persisted": True}]
    assert response.json()["authorizes_field_work"] is False


def test_demo_start_rejects_unlabelled_or_real_location_claims() -> None:
    event = demo_order_event("start")
    event["payload"]["data_status"] = "real"
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [event],
        },
    )
    assert response.status_code == 422

    event = demo_order_event("start")
    del event["payload"]["simulation_method"]
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [event],
        },
    )
    assert response.status_code == 422


def test_sync_contract_accepts_only_unuploaded_unvalidated_photo_manifest() -> None:
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [photo_manifest_event()],
        },
    )
    assert response.status_code == 200
    assert response.json()["accepted"] == [{"event_id": str(EVENT_ID), "persisted": True}]

    for field, unsafe_value in (
        ("content_status", "uploaded"),
        ("ruler_status", "valid"),
        ("eligible_for_official_reporting", True),
    ):
        unsafe = photo_manifest_event()
        unsafe["payload"][field] = unsafe_value
        response = request_with_overrides(
            endpoint="/v1/sync/batch",
            payload={
                "device_id": str(DEVICE_ID),
                "batch_id": str(BATCH_ID),
                "base_sync_cursor": 0,
                "events": [unsafe],
            },
        )
        assert response.status_code == 422


class DemoValidationCursor:
    def __init__(self, *, operations: set[str], measurement_count: int = 3) -> None:
        self.operations = operations
        self.measurement_count = measurement_count
        self.query = ""

    async def execute(self, query: str, parameters: tuple) -> None:
        self.query = query

    async def fetchone(self) -> tuple:
        if "FROM work_order order_record" in self.query:
            return ("prepared", "prepared", False, False, False, True)
        return (self.measurement_count,)

    async def fetchall(self) -> list[tuple[str]]:
        return [(operation,) for operation in self.operations]


class PhotoValidationCursor:
    def __init__(self, target: tuple | None, *, existing_photo: bool = False) -> None:
        self.target = target
        self.existing_photo = existing_photo
        self.query = ""

    async def execute(self, query: str, parameters: tuple) -> None:
        self.query = query

    async def fetchone(self) -> tuple | None:
        if "WHERE photo_id" in self.query:
            return (EVENT_ID,) if self.existing_photo else None
        return self.target


def validate_photo_manifest(target: tuple | None, *, existing_photo: bool = False):
    event = MobileSyncEventRequest.model_validate(photo_manifest_event())
    return asyncio.run(
        PostgresMobileSyncRepository._validate_photo_manifest(
            PhotoValidationCursor(  # type: ignore[arg-type]
                target, existing_photo=existing_photo
            ),
            USER_ID,
            event,
        )
    )


def test_photo_manifest_requires_exact_prepared_point_and_road_access() -> None:
    eligible = (ORDER_ID, "prepared", "prepared", False, False, False, False, True)
    assert validate_photo_manifest(eligible) is None
    assert validate_photo_manifest(None).code == "planned_point_not_found"
    assert validate_photo_manifest((UUID(int=0), *eligible[1:])).code == "point_order_mismatch"
    assert validate_photo_manifest((*eligible[:7], False)).code == "road_access_denied"
    assert validate_photo_manifest(eligible, existing_photo=True).code == "photo_id_reused"


def validate_demo_event(operation: str, *, operations: set[str], measurement_count: int = 3):
    event = MobileSyncEventRequest.model_validate(demo_order_event(operation))
    cursor = DemoValidationCursor(
        operations=operations,
        measurement_count=measurement_count,
    )
    return asyncio.run(
        PostgresMobileSyncRepository._validate_demo_order_event(
            cursor,
            USER_ID,
            event,  # type: ignore[arg-type]
        )
    )


def test_demo_order_sequence_requires_confirm_then_start_then_finish() -> None:
    assert validate_demo_event("confirm", operations=set()) is None
    assert validate_demo_event("start", operations=set()).code == "invalid_demo_sequence"
    assert validate_demo_event("start", operations={"confirm"}) is None
    assert validate_demo_event("finish", operations={"confirm"}).code == "invalid_demo_sequence"
    assert (
        validate_demo_event("finish", operations={"confirm", "start"}, measurement_count=2).code
        == "measurements_incomplete"
    )
    assert (
        validate_demo_event("finish", operations={"confirm", "start"}, measurement_count=3) is None
    )


def test_measurement_requires_prepared_and_non_official_labels() -> None:
    event = measurement_event()
    del event["payload"]["eligible_for_official_reporting"]
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [event],
        },
    )

    assert response.status_code == 422


def test_zero_centimeters_is_a_valid_prepared_n1_measurement() -> None:
    event = measurement_event()
    event["payload"]["height_cm"] = 0
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [event],
        },
    )

    assert response.status_code == 200
    assert response.json()["accepted"][0]["event_id"] == str(EVENT_ID)


def test_batch_rejects_duplicate_event_ids_before_persistence() -> None:
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [measurement_event(), measurement_event()],
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (MobileDeviceNotRegisteredError, 403),
        (MobileDeviceOwnershipError, 403),
        (MobileDeviceRevokedError, 403),
        (MobileSyncBatchConflictError, 409),
        (MobileSyncCursorAheadError, 409),
    ],
)
def test_sync_domain_failures_have_stable_http_statuses(
    failure: type[Exception], expected_status: int
) -> None:
    response = request_with_overrides(
        endpoint="/v1/sync/batch",
        payload={
            "device_id": str(DEVICE_ID),
            "batch_id": str(BATCH_ID),
            "base_sync_cursor": 0,
            "events": [measurement_event()],
        },
        failure=failure,
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize("endpoint", ["/v1/mobile/devices", "/v1/sync/batch"])
def test_mobile_sync_endpoints_require_bearer_authentication(endpoint: str) -> None:
    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(endpoint, json={})

    response = asyncio.run(request())

    assert response.status_code == 401
