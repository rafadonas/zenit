from datetime import UTC, datetime
from uuid import UUID

import pytest

from zenit_geospatial.planet_quota import (
    CONSUMING_ORDER_STATES,
    QuotaBudget,
    QuotaError,
    QuotaStatus,
    QuotaUsage,
)
from zenit_geospatial.planet_quota_cli import build_parser, run

BUDGET = QuotaBudget(
    id=UUID("44000000-0000-4000-8000-000000000001"),
    period_start=datetime(2026, 9, 1, tzinfo=UTC),
    period_end=datetime(2026, 10, 1, tzinfo=UTC),
    max_area_m2=30_000.0,
    max_bytes=314_572_800,
    max_orders=3,
    approval_reference="planet-budget-2026-09",
    approved_by="data owner",
)


def status(orders: int = 0, area_m2: float = 0.0, used_bytes: int = 0) -> QuotaStatus:
    return QuotaStatus(budget=BUDGET, usage=QuotaUsage(orders, area_m2, used_bytes))


def test_remaining_values_subtract_recorded_consumption() -> None:
    current = status(orders=1, area_m2=9_000.0, used_bytes=104_857_600)

    assert current.remaining_orders == 2
    assert current.remaining_area_m2 == pytest.approx(21_000.0)
    assert current.remaining_bytes == 209_715_200


def test_request_within_the_budget_is_allowed() -> None:
    status(orders=1, area_m2=9_000.0).ensure_capacity(area_m2=10_000, requested_bytes=104_857_600)


def test_area_over_the_remaining_budget_is_refused() -> None:
    with pytest.raises(QuotaError, match="exceeds the remaining"):
        status(area_m2=25_000.0).ensure_capacity(area_m2=10_000, requested_bytes=1_000)


def test_bytes_over_the_remaining_budget_are_refused() -> None:
    with pytest.raises(QuotaError, match="bytes exceed the remaining"):
        status(used_bytes=300_000_000).ensure_capacity(area_m2=100, requested_bytes=104_857_600)


def test_order_count_over_the_budget_is_refused() -> None:
    with pytest.raises(QuotaError, match="orders in the period"):
        status(orders=3).ensure_capacity(area_m2=100, requested_bytes=1_000)


def test_non_positive_requests_are_rejected() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        status().ensure_capacity(area_m2=0, requested_bytes=1_000)


def test_cancelled_orders_do_not_consume_the_budget() -> None:
    assert "cancelled" not in CONSUMING_ORDER_STATES
    assert set(CONSUMING_ORDER_STATES) == {"queued", "running", "success", "failed"}


def test_report_exposes_limits_usage_and_remaining() -> None:
    report = status(orders=1, area_m2=9_000.0, used_bytes=104_857_600).as_report()

    assert report["approval_reference"] == "planet-budget-2026-09"
    assert report["used_orders"] == 1
    assert report["remaining_orders"] == 2
    assert report["used_area_m2"] == 9_000.0
    assert report["remaining_area_m2"] == 21_000.0
    assert report["remaining_bytes"] == 209_715_200
    assert report["counted_order_states"] == list(CONSUMING_ORDER_STATES)


def test_quota_cli_reports_without_touching_the_database() -> None:
    arguments = build_parser().parse_args(["--at", "2026-09-15T12:00:00+00:00"])

    report = run(arguments, quota_status=status(orders=2))

    assert report["remaining_orders"] == 1


def test_quota_cli_requires_an_offset_aware_instant() -> None:
    arguments = build_parser().parse_args(["--at", "2026-09-15T12:00:00"])

    with pytest.raises(ValueError, match="UTC offset"):
        run(arguments, quota_status=status())


def test_order_command_refuses_a_compose_only_destination_before_any_call() -> None:
    from zenit_api.config import Settings
    from zenit_geospatial.planet_order_cli import build_parser as order_parser
    from zenit_geospatial.planet_order_cli import run as order_run

    arguments = order_parser().parse_args(["--execute"])
    settings = Settings(
        _env_file=None,
        PL_API_KEY="private-planet-key",
        DATABASE_URL="postgresql+psycopg://zenit:pw@postgres:5432/zenit",
    )

    with pytest.raises(RuntimeError, match="only reachable inside Compose"):
        order_run(arguments, settings, quota_status=status())
