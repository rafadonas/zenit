# ADR-0024: Prepared post-inspection proposal

- Status: accepted
- Date: 2026-08-11

## Context

The prepared inspection summary closes the simulated evidence return but does
not translate the reviewed typed measurements into the next planning signal.
The master flow calls for a mowing proposal when inspection confirms a threshold
breach. With simulated location and prepared measurements, that signal must not
be confused with real confirmation, approval, a mowing order, or authorization.

## Decision

Create a versioned prepared post-inspection policy with the project thresholds:
30 cm for left, right, and median zones and 10 cm for special zones. An
authenticated current manager or supervisor may create one immutable,
idempotent proposal from one prepared summary. PostgreSQL recomputes the
applicable threshold and compares it with the summary's typed maximum height.

Return `mowing_review` only when the maximum is strictly above the applicable
threshold; otherwise return `monitor`. Every proposal requires a separate human
review and remains simulated-location, prepared reviewed non-operational,
ineligible for model training or official reporting, and incapable of creating
or authorizing field work. Expose only proposals from roads covered by the
actor's current non-simulated role.

The dashboard displays the threshold comparison beside the summary and labels
the proposal as awaiting a human decision. It provides no mowing-order action.

## Consequences

- The prepared loop reaches an explainable post-inspection planning signal.
- The 10/30 cm rule is enforced both in the API calculation and by PostgreSQL.
- Simulated measurements cannot silently become operational confirmation.
- Append-only human proposal decisions and any subsequent prepared mowing-order
  foundation remain the next separately controlled increments.
