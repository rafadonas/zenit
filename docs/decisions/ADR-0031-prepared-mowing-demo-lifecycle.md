# ADR-0031: Prepared mowing demo lifecycle

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0030 made the prepared mowing-planning chain available to the mobile app
for offline read-only review. A later demonstration needs to rehearse lifecycle
transitions without implying that planning approval is operational approval or
that any field execution occurred.

The project still lacks official operational approval, dual-approval,
dispatch, team/equipment assignment, location, safety, and weather evidence.

## Decision

Accept an append-only, idempotent sync sequence for a mowing-order rehearsal:
`confirm`, `start`, balanced `pause`/`resume`, and `finish`. Serialize validation
per mowing order and require monotonically non-decreasing client timestamps.

Require the effective prepared resource plan, manual readiness assessment, and
planning approval, plus an active road-scoped manager or supervisor role. The
start event uses only an explicitly simulated demonstration coordinate; all
other events collect no location.

Persist every event as `simulated` with `demo_only` and
`mowing_demo_rehearsal_only` scopes. Fix operational approval, field
authorization, execution eligibility, model-training eligibility, and official
reporting eligibility to false in both API validation and PostgreSQL checks.
The database independently verifies the exact accepted sync payload and keeps
the event immutable.

## Consequences

- The server can preserve and replay a safe mowing-lifecycle rehearsal.
- A planning decision cannot be promoted into operational approval.
- The rehearsal cannot mutate the prepared mowing order or claim real field
  work, device location, dispatch, tracking, or completion.
- Mobile controls, real evidence capture, official policy, and operational
  execution remain future work requiring explicit approval.
