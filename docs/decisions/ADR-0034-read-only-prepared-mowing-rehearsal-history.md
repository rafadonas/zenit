# ADR-0034: Read-only prepared mowing rehearsal history

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0031 and ADR-0032 preserve a simulated mowing rehearsal as immutable,
idempotent mobile-sync events. After synchronization, managers could still not
inspect that sequence in the management dashboard. Treating the final `finish`
event as a real mowing outcome would be unsafe because the project has no
operational approval, dispatch, verified location, post-service measurement,
or post-service photo evidence.

## Decision

Expose an authenticated, road-role-scoped read projection at
`GET /v1/prepared-mowing-rehearsals`. Return only prepared mowing orders that
retain every execution block. Do not expose actor, device, coordinate, or
simulation-method details.

Derive `not_started`, `confirmed`, `in_progress`, `paused`, or `finished` from
the append-only event order. Revalidate increasing event sequence, monotonic
client timestamps, allowed transitions, simulated start location status, and
every false operational/reporting/training flag before returning the contract.
Also derive event count, pause count, start/finish timestamps, and the recorded
span between start and the latest event. The span is not operational duration.

Render the same guarded contract in the management dashboard as a timeline.
Label a terminal state as **Ensaio finalizado**, with an explicit
`rehearsal_only_no_field_completion_claim` status. It must not update the road
map, historical vegetation class, mowing-order status, or official report.

## Consequences

- A manager can audit what the offline demonstration synchronized.
- Invalid ordering, time reversal, status promotion, or unsafe order state
  fails closed instead of producing a misleading history.
- The projection requires no mutable summary table or new migration; immutable
  events remain the source of truth.
- Verified post-service measurements, photos, exceptions, operational outcome,
  and map/history updates remain separate P0 work.
