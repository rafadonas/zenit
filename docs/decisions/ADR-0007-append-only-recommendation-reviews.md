# ADR-0007: Append-only recommendation reviews

- Status: accepted
- Date: 2026-08-07

## Update

ADR-0008 satisfies the identity, RBAC, and policy preconditions for an
authenticated review-write endpoint. The review remains separate from and
incapable of authorizing field work.

## Context

The analysis baseline records whether human approval is required, but that flag
is not evidence that a person reviewed a recommendation. Sprint 4 requires
acceptance, rejection, and adjustment with an auditable actor and proportional
rationale. A review must not silently become a field-work authorization.

## Decision

Store human review events in PostgreSQL as append-only
`recommendation_review` rows linked to the exact `vegetation_analysis` result.
Each event records an idempotency key, decision, optional adjusted
recommendation, rationale, identity-provider subject, source channel, event
time, and structured metadata.

Rejected and adjusted outcomes require a non-blank rationale. Adjusted outcomes
require an explicit replacement recommendation. Corrections insert a new event
that references the review it supersedes; a database guard requires both rows
to refer to the same analysis. Update and delete triggers protect the audit
trail.

This table does not create a work order and does not authorize field activity.
No write endpoint is introduced until authenticated identity, RBAC, and the
applicable single/dual-approval policy are defined and versioned.

## Consequences

- A boolean approval flag can no longer be confused with proof of review.
- Human decisions retain the analysis, rule, processor, and data provenance
  reachable through foreign keys.
- Review corrections preserve the earlier event rather than rewriting history.
- Reviewer subjects are personal/security-sensitive identifiers and must not be
  logged, committed as fixtures from production, or exposed without RBAC.
- Work-order creation remains a separate future transaction with an explicit
  link to the effective review decision.
