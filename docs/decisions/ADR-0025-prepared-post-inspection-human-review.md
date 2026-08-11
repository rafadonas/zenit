# ADR-0025: Prepared post-inspection human review

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0024 creates a threshold-based prepared planning proposal but deliberately
leaves the human-decision state pending. Accepting a `mowing_review` signal must
not be confused with authorizing mowing, and corrections must preserve the
earlier decision instead of rewriting it.

## Decision

Record authenticated proposal decisions as immutable, idempotent events linked
to the exact proposal and its versioned policy. Allow `accepted`, `rejected`, or
`adjusted`; an adjustment must choose `monitor` or `mowing_review`. Rejection and
adjustment require a rationale. Acceptance means agreement with the prepared
planning signal only.

Keep one linear effective review per proposal. The first event cannot supersede
another review; every correction must supersede the current effective leaf.
Serialize inserts per proposal with a PostgreSQL advisory transaction lock and
enforce a unique child for every superseded event. PostgreSQL repeats active
reviewer, current non-simulated road role, exact proposal policy, prepared-data,
non-official, and non-authorizing checks.

Expose the effective decision and total review count in the actor-scoped
proposal collection without exposing reviewer identity. Dashboard writes pass
through exact-origin, CSRF, UUID, idempotency, and allowlist validation.

## Consequences

- Human acceptance is auditable but remains incapable of creating field work.
- Corrections preserve a complete, unambiguous decision chain.
- Adjusting to `mowing_review` still means “review for planning,” not “mow.”
- A prepared mowing-order foundation, team assignment, and any operational
  authorization remain separate future increments requiring explicit controls.
