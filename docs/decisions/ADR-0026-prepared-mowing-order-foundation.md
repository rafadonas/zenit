# ADR-0026: Prepared mowing-order foundation

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0025 records the human decision on a prepared post-inspection proposal. An
effective `mowing_review` decision is sufficient to continue planning, but the
available evidence still uses simulated location and prepared measurements. It
cannot authorize an operational mowing activity.

## Decision

Create an immutable, idempotent prepared mowing order only from the current
effective proposal review. An accepted review inherits the proposal action; an
adjusted review uses its replacement. Rejected, superseded, and effective
`monitor` decisions cannot create an order.

Link the order to the exact review, proposal, and source inspection order.
Serialize creation with the same per-proposal advisory lock used by human
review corrections. Require an active manager or supervisor assignment for the
road, using the roles in versioned policy `prepared-mowing-order-v1`. Repeat
source, policy, role, and safety checks in PostgreSQL.

Fix every order to prepared, simulated-location, non-official, and
non-executable state. Team and equipment remain unassigned; weather and safety
checks remain pending; a separate operational approval remains required. The
request cannot set any of these fields. API reads label whether the exact source
review remains effective or has since been superseded.

## Consequences

- Every prepared mowing order has an exact effective human decision as source.
- A later corrected review may create a new prepared order while preserving the
  previous order as audit history.
- The dashboard exposes a planning action only for an effective
  `mowing_review` decision and labels the result as non-executable.
- Team assignment, equipment, weather, safety, scheduling, mobile mowing
  execution, and operational authorization remain separate future increments.
