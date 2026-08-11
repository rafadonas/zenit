# ADR-0032: Mobile prepared mowing demo orchestration

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0031 added a server boundary for an append-only simulated mowing
rehearsal. The mobile app could inspect the prepared planning chain but could
not yet create, retain, or synchronize those rehearsal events offline.

The source plan still has no operational approval, verified resources,
dispatch, real location, or execution evidence. Mobile controls therefore must
not resemble or claim real field-work authorization.

## Decision

Add a separate encrypted mobile lifecycle for `confirm`, `start`, balanced
`pause`/`resume`, and `finish`. Create event and batch UUIDs before network use,
retain the exact pending batch across retries, and preserve accepted, rejected,
or conflicting results.

Enable the rehearsal only for the effective prepared plan whose manual weather
and safety declarations are both `clear` and whose decision is
`approved_for_planning`. Require the linked prepared inspection snapshot and
reuse its first estimated planned point as the start's explicitly simulated
coordinate. Do not access a device location service.

Keep the events separate from inspection measurements and photos. Label every
payload `simulated`, `demo_only`, and `mowing_demo_rehearsal_only`; fix
operational approval, field authorization, execution eligibility,
model-training eligibility, and official-reporting eligibility to false.
Render an unmistakable warning that these controls record an offline rehearsal,
not dispatch or field execution.

This decision supersedes only ADR-0030's temporary prohibition on mobile
mowing-rehearsal controls. Its read-only planning data, fail-closed parsing,
and non-operational safety boundaries remain in force.

## Consequences

- The mowing rehearsal works offline and retries idempotently with stable IDs.
- Pause and resume must remain balanced before finish and synchronization.
- Missing source points, stale planning decisions, unsafe readiness, promoted
  flags, and invalid sequences fail closed.
- No real GPS, tracking, mowing evidence, dispatch, operational approval, or
  official completion is introduced.
