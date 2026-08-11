# ADR-0029: Prepared mowing planning approval

- Status: accepted
- Date: 2026-08-11

## Context

The manual requires human approval and may require manager plus supervisor in
critical scenarios. The project does not yet have official criticality,
cost/area, or dual-approval policy values. The available mowing order,
resources, weather, and safety context also remains prepared or unverified.

## Decision

Create a separate immutable decision event for `approved_for_planning`,
`changes_requested`, or `rejected`. A positive planning decision requires the
effective manual readiness assessment to have `clear` weather and safety
results. Every decision requires rationale.

Maintain one linear correction chain per readiness-assessment version and use
the established proposal, resource, readiness, then approval lock order.
Repeat current-source, policy, role, decision, and safety checks in PostgreSQL.

Fix the decision effect to `planning_only_no_execution_authorization`. It never
satisfies operational approval and never authorizes field execution. Mark the
dual-approval requirement as `pending_official_policy_validation`; do not infer
whether this prepared scenario needs one or two approvers.

## Consequences

- Planning approval is auditable and clearly segregated from execution rights.
- Changes to readiness start a new planning-decision chain and preserve the old
  decision as history.
- No positive decision can silently promote simulated or unverified data.
- Official criticality and dual-approval rules, verified resources/evidence,
  scheduling, dispatch, and field execution remain future work.
