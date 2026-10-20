"""PLANET-005: approved Planet consumption budget and fail-closed capacity checks.

Consumption is derived from ``planet_order`` instead of a parallel counter, so an
Order that was created is always accounted for, even when its download failed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg

# A cancelled Order never reaches the provider, so it does not consume the account budget.
CONSUMING_ORDER_STATES = ("queued", "running", "success", "failed")


class QuotaError(RuntimeError):
    """Raised when the approved budget cannot cover a request."""


@dataclass(frozen=True, slots=True)
class QuotaBudget:
    id: UUID
    period_start: datetime
    period_end: datetime
    max_area_m2: float
    max_bytes: int
    max_orders: int
    approval_reference: str
    approved_by: str


@dataclass(frozen=True, slots=True)
class QuotaUsage:
    orders: int
    area_m2: float
    bytes: int


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    budget: QuotaBudget
    usage: QuotaUsage

    @property
    def remaining_area_m2(self) -> float:
        return self.budget.max_area_m2 - self.usage.area_m2

    @property
    def remaining_bytes(self) -> int:
        return self.budget.max_bytes - self.usage.bytes

    @property
    def remaining_orders(self) -> int:
        return self.budget.max_orders - self.usage.orders

    def ensure_capacity(self, *, area_m2: float, requested_bytes: int) -> None:
        """Refuse before any external call when the request exceeds the approved budget."""
        if area_m2 <= 0 or requested_bytes <= 0:
            raise ValueError("area_m2 and requested_bytes must be positive")
        if self.remaining_orders < 1:
            raise QuotaError(
                f"approved budget allows {self.budget.max_orders} orders in the period and "
                f"{self.usage.orders} were already created"
            )
        if area_m2 > self.remaining_area_m2:
            raise QuotaError(
                f"requested area {area_m2:.2f} m2 exceeds the remaining "
                f"{self.remaining_area_m2:.2f} m2 of the approved budget"
            )
        if requested_bytes > self.remaining_bytes:
            raise QuotaError(
                f"requested {requested_bytes} bytes exceed the remaining "
                f"{self.remaining_bytes} bytes of the approved budget"
            )

    def as_report(self) -> dict[str, object]:
        return {
            "budget_id": str(self.budget.id),
            "approval_reference": self.budget.approval_reference,
            "approved_by": self.budget.approved_by,
            "period_start": self.budget.period_start.isoformat(),
            "period_end": self.budget.period_end.isoformat(),
            "max_orders": self.budget.max_orders,
            "used_orders": self.usage.orders,
            "remaining_orders": self.remaining_orders,
            "max_area_m2": round(self.budget.max_area_m2, 2),
            "used_area_m2": round(self.usage.area_m2, 2),
            "remaining_area_m2": round(self.remaining_area_m2, 2),
            "max_bytes": self.budget.max_bytes,
            "used_bytes": self.usage.bytes,
            "remaining_bytes": self.remaining_bytes,
            "counted_order_states": list(CONSUMING_ORDER_STATES),
        }


class PostgresPlanetQuota:
    """Reads the approved budget and the consumption already recorded in ``planet_order``."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def status(self, at: datetime) -> QuotaStatus:
        if at.tzinfo is None:
            raise ValueError("at must be timezone-aware")
        budget_query = """
            SELECT id, period_start, period_end, max_area_m2, max_bytes, max_orders,
                   approval_reference, approved_by
            FROM planet_quota_budget
            WHERE %s >= period_start AND %s < period_end
        """
        usage_query = """
            SELECT count(*), coalesce(sum(aoi_area_m2), 0), coalesce(sum(downloaded_bytes), 0)
            FROM planet_order
            WHERE created_at >= %s AND created_at < %s
              AND order_state = ANY(%s)
        """
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(budget_query, (at, at))
            row = cursor.fetchone()
            if row is None:
                raise QuotaError(
                    "no approved Planet quota budget covers this instant; "
                    "record one before creating an Order"
                )
            budget = QuotaBudget(
                id=row[0],
                period_start=row[1],
                period_end=row[2],
                max_area_m2=float(row[3]),
                max_bytes=int(row[4]),
                max_orders=int(row[5]),
                approval_reference=row[6],
                approved_by=row[7],
            )
            cursor.execute(
                usage_query,
                (budget.period_start, budget.period_end, list(CONSUMING_ORDER_STATES)),
            )
            used = cursor.fetchone()
        return QuotaStatus(
            budget=budget,
            usage=QuotaUsage(orders=int(used[0]), area_m2=float(used[1]), bytes=int(used[2])),
        )
