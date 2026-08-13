# ADR-0050: Dashboard simulated mowing post-service exception

- Status: accepted
- Date: 2026-08-13

## Decision

Expose simulated mowing post-service exception assessments in the authenticated
dashboard. The dashboard loads actor-scoped exceptions, shows whether the
summary recommends `inspect_follow_up` or `monitor`, and offers a CSRF-checked
creation action from an existing simulated post-service summary.

The dashboard forwards only the human-entered rationale and idempotency key.
The API remains authoritative for role checks, threshold selection, idempotency,
and safety labels.

This presentation does not create operational history, map updates, field
authorization, mowing completion claims, model-training data, or official
reports.
