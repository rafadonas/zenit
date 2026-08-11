# ADR-0028: Prepared mowing readiness assessment

- Status: accepted
- Date: 2026-08-11

## Context

The prepared mowing order and candidate resource plan still lack weather and
safety evidence. The repository has neither a weather integration nor an
official Motiva safety protocol. A manual statement must not be presented as an
operational clearance.

## Decision

Record separate weather and safety results as immutable, idempotent manual
assessment events linked to the current candidate resource plan. Allow
`clear`, `blocked`, or `inconclusive`, but require a declared source reference
for each result and an overall rationale. Label every event
`prepared_manual_pending_validation`.

Maintain one linear correction chain per resource-plan version. Acquire locks
in proposal-review, resource-plan, then readiness order so corrections cannot
race against obsolete source state. Require an active manager or supervisor
role for the road and repeat all source, policy, role, and safety checks in
PostgreSQL.

No result, including `clear` for both dimensions, authorizes field work or
makes the order executable. Operational approval remains mandatory.

## Consequences

- Manual climate and safety context becomes auditable without pretending to be
  live, official, or validated evidence.
- Correcting candidate resources starts a separate readiness chain for the new
  resource-plan version; the earlier assessment remains historical.
- Weather integration, official checklists, scheduling, verified assignments,
  and operational approval remain future increments.
