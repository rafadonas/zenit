# ADR-0030: Read-only prepared mowing planning on mobile

- Status: accepted
- Date: 2026-08-11
- Superseded in part by: ADR-0032 (mobile rehearsal controls only)

## Context

The Android-first app already downloads prepared inspection orders for an
explicitly simulated demonstration workflow. Prepared mowing orders now have
candidate resources, manual readiness assessments, and segregated planning
decisions, but none of these records authorizes operational work.

Exposing that planning context in the field app is useful for offline review,
provided the mobile boundary cannot turn planning state into dispatch or
execution state.

## Decision

Download actor-scoped prepared mowing orders from
`GET /v1/prepared-mowing-orders` and retain their snapshots in the existing
encrypted, user-bound offline vault. Include the effective candidate resource
plan, manual weather and safety assessment, and planning decision with their
source links and counts.

Validate the complete chain at both API and mobile boundaries. The mobile
parser fails closed unless the record remains `prepared`, uses a simulated
location, has unassigned team and equipment, keeps operational weather and
safety checks pending, requires unsatisfied operational approval, and sets all
execution, model-training, and official-report flags to false. Readiness must
refer to the effective resource plan and a planning decision must refer to the
effective readiness assessment.

Render this information as an offline read-only demonstration. Do not add
mobile methods or controls to confirm, start, track, finish, dispatch, approve
operationally, or synchronize mowing execution.

## Consequences

- Authorized users can inspect the latest prepared mowing-planning context
  offline without converting it into field authority.
- Logout and session expiry hide the snapshot while retaining its encrypted
  cache under the existing owner binding.
- A positive planning decision is visibly distinguished from operational
  approval and remains non-executable.
- Real locations, verified resources and evidence, scheduling, dispatch,
  execution telemetry, and official reporting remain future work.
