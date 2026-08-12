# ADR-0035: Simulated mowing post-service measurement foundation

- Status: accepted
- Date: 2026-08-11

## Context

The simulated mowing rehearsal has an immutable lifecycle and a management
history, but it has no evidence recorded after its terminal event. Reusing the
inspection measurements as a mowing result would erase the before/after
boundary. Treating demo input as real field evidence would also misrepresent
the lack of operational approval, verified GPS, photos, and execution.

## Decision

Add a separate `mowing_measurement/create` mobile-sync event and persist it in
`prepared_mowing_post_service_measurement`. Bind every event to the prepared
mowing order, its effective planning approval, and one of the three planned
points from the source inspection order.

Accept a measurement only after the same planning approval has a persisted
`finish` rehearsal event. Serialize writes with the existing mowing-demo lock,
allow one immutable measurement per mowing-order/point pair, and require the
client timestamp to be at or after the rehearsal finish.

Fix the phase to `post_service`, scope to
`mowing_demo_post_service_only`, data status to `simulated`, quality to
`simulated_unverified`, and both location and photo status to `not_collected`.
Keep operational approval, field authorization, execution eligibility,
model-training eligibility, and official-reporting eligibility false in the
API model and PostgreSQL constraints. PostgreSQL independently verifies the
exact accepted sync payload and repeats actor, device, road-role, planning,
source-point, and order safety checks.

## Consequences

- Post-service heights no longer reuse or overwrite inspection measurements.
- A retry remains idempotent through the existing event/batch contract, while a
  second event for the same point is rejected instead of becoming an implicit
  correction.
- A height is only simulated, unverified typed input; it does not prove mowing,
  photo quality, GPS, operational completion, or vegetation condition.
- Mobile capture UI, post-service photos, human review, three-point summary,
  threshold exception handling, and map/history updates remain separate P0
  increments.
