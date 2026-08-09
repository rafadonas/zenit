# ADR-0014: Simulated prepared-order lifecycle

- Status: accepted
- Date: 2026-08-09

## Context

Sprint 5 requires an offline confirm/start/finish demonstration with simulated
GPS. Existing orders and planned points remain prepared, estimated, and
ineligible for field execution. Mutating their status or presenting a demo
coordinate as observed evidence would cross the operational safety boundary.

## Decision

Accept `work_order/confirm`, `work_order/start`, and `work_order/finish` through
the idempotent mobile sync boundary only when their payload is explicitly
`simulated`, `demo_only`, non-authorizing, and ineligible for official reports.
Start requires a simulated EPSG:4326 coordinate and the versioned method
`prepared_point_demo_v1`; confirm and finish state that location was not
collected.

Persist lifecycle events append-only in a separate table without updating the
immutable prepared order. Serialize event processing per order and require the
exact sequence once. Finish additionally requires prepared measurements for
all three distinct planned points. Repeat payload, actor/device, road-role,
order-state, sequence, and measurement-completeness checks in PostgreSQL.

## Consequences

- The demo can represent a complete sequence without claiming a real
  inspection or surveyed GPS evidence.
- Idempotent replay uses the existing event and batch identifiers.
- A second lifecycle event or an out-of-order event is persistently rejected.
- The Flutter client is not yet wired to create these events; this server
  foundation must land before the offline UI can safely expose the lifecycle.
- Real GPS capture, photographs, operational authorization, and reporting
  remain separate future increments.
