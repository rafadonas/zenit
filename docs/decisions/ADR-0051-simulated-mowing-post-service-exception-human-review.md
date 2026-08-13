# ADR-0051: Simulated mowing post-service exception human review

- Status: accepted
- Date: 2026-08-13

## Decision

Record human decisions for simulated mowing post-service exceptions as immutable
and idempotent review events.

Reviewers can accept, reject, or adjust an exception recommendation. Adjustments
are limited to the non-operational outcomes `monitor` and `inspect_follow_up`.
Rejected and adjusted decisions require a rationale, and subsequent decisions
must explicitly supersede the current effective review.

Each review keeps `phase=post_service`, `data_status=simulated`,
`eligible_for_official_reporting=false`, and `authorizes_field_work=false`.

## Consequences

The review trail can explain why a simulated exception was accepted, rejected,
or changed for follow-up review, but it does not update operational maps,
service history, official reports, model-training datasets, mowing completion,
or field dispatch.

API and database checks both enforce actor road roles, exact policy linkage,
idempotency replay, append-only persistence, and effective-review
supersession.
