import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.mowing_rehearsals import (
    PreparedMowingRehearsalCollection,
    PreparedMowingRehearsalEvent,
    PreparedMowingRehearsalSummary,
    derive_rehearsal_metrics,
    get_prepared_mowing_rehearsal_reader,
)

ACTOR = AuthenticatedUser(
    id=UUID("95000000-0000-4000-8000-000000000001"),
    email="manager@example.test",
    display_name="Prepared Manager",
)
MOWING_ORDER_ID = UUID("95000000-0000-4000-8000-000000000002")
PLANNING_APPROVAL_ID = UUID("95000000-0000-4000-8000-000000000003")
STARTED_AT = datetime(2026, 8, 11, 20, 5, tzinfo=UTC)


def event(
    operation: str,
    sequence: int,
    seconds: int,
    **changes,
) -> PreparedMowingRehearsalEvent:
    values = {
        "event_id": UUID(f"95000000-0000-4000-8000-{sequence:012d}"),
        "event_sequence": sequence,
        "source_planning_approval_id": PLANNING_APPROVAL_ID,
        "operation": operation,
        "client_occurred_at": STARTED_AT + timedelta(seconds=seconds),
        "location_status": "simulated" if operation == "start" else "not_collected",
        "simulation_scope": "demo_only",
        "rehearsal_scope": "mowing_demo_rehearsal_only",
        "data_status": "simulated",
        "operational_approval_satisfied": False,
        "authorizes_field_work": False,
        "eligible_for_field_execution": False,
        "eligible_for_model_training": False,
        "eligible_for_official_reporting": False,
    }
    return PreparedMowingRehearsalEvent.model_validate(values | changes)


def finished_events() -> list[PreparedMowingRehearsalEvent]:
    return [
        event("confirm", 10, 0),
        event("start", 11, 5),
        event("pause", 12, 35),
        event("resume", 13, 50),
        event("finish", 14, 95),
    ]


def summary() -> PreparedMowingRehearsalSummary:
    events = finished_events()
    metrics = derive_rehearsal_metrics(events)
    return PreparedMowingRehearsalSummary(
        mowing_order_id=MOWING_ORDER_ID,
        road_code="SP-021",
        segment_index=195,
        zone_type="left",
        rehearsal_state=metrics.state,
        event_count=metrics.event_count,
        pause_count=metrics.pause_count,
        started_at=metrics.started_at,
        finished_at=metrics.finished_at,
        recorded_span_seconds=metrics.recorded_span_seconds,
        events=events,
    )


def test_derives_finished_rehearsal_without_claiming_field_completion() -> None:
    result = summary()
    assert result.rehearsal_state == "finished"
    assert result.event_count == 5
    assert result.pause_count == 1
    assert result.recorded_span_seconds == 90
    assert result.completion_claim_status == (
        "rehearsal_only_no_field_completion_claim"
    )
    assert result.operational_approval_satisfied is False
    assert result.authorizes_field_work is False
    assert result.eligible_for_official_reporting is False


def test_rejects_an_invalid_or_time_reversed_event_history() -> None:
    with pytest.raises(ValueError, match="invalid prepared mowing rehearsal sequence"):
        derive_rehearsal_metrics([event("confirm", 1, 0), event("finish", 2, 5)])
    with pytest.raises(ValueError, match="time cannot move backwards"):
        derive_rehearsal_metrics(
            [event("confirm", 1, 10), event("start", 2, 5)]
        )


def test_rejects_promoted_event_and_inconsistent_summary() -> None:
    with pytest.raises(ValidationError):
        event("confirm", 1, 0, authorizes_field_work=True)
    with pytest.raises(ValidationError, match="does not match its immutable events"):
        PreparedMowingRehearsalSummary.model_validate(
            summary().model_dump() | {"rehearsal_state": "in_progress"}
        )


class FakeReader:
    async def list_for_actor(self, **values) -> PreparedMowingRehearsalCollection:
        assert values == {"actor": ACTOR, "limit": 9}
        return PreparedMowingRehearsalCollection(
            items=[summary()], result_count=1, limit=9, truncated=False
        )


def request(*, authenticated: bool = True):
    async def fake_actor():
        return ACTOR

    async def fake_reader():
        return FakeReader()

    async def execute():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_prepared_mowing_rehearsal_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/v1/prepared-mowing-rehearsals?limit=9")
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(execute())


def test_lists_actor_scoped_rehearsal_history_without_identity_or_location() -> None:
    response = request()
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["rehearsal_state"] == "finished"
    assert payload["items"][0]["events"][1]["location_status"] == "simulated"
    assert "longitude" not in response.text
    assert "actor" not in response.text
    assert "device" not in response.text
    assert "not field execution" in payload["warning"]


def test_rehearsal_history_requires_authentication() -> None:
    assert request(authenticated=False).status_code == 401
