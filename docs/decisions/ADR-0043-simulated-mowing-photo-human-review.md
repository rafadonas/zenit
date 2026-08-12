# ADR-0043: Simulated mowing-photo human review

- Status: accepted
- Date: 2026-08-12

## Context

ADR-0042 allows authorized retrieval of exact simulated post-service photo
bytes, but transport integrity and successful decryption do not establish image
quality or ruler visibility. Reusing the inspection review would erase the
post-service phase and simulated mowing scope.

## Decision

Create a separate versioned prepared policy, append-only human-review table,
authenticated queue, and decision endpoint for simulated mowing post-service
photos. Allow current non-simulated manager/supervisor road roles and derive the
reviewer only from the authenticated token.

Record `accepted`, `rejected`, or `inconclusive`, image quality, ruler
visibility, rationale, policy version, timestamp, idempotency hash, and optional
supersession. Acceptance requires accepted quality and a visible ruler;
rejection and inconclusive outcomes require rationale. Serialize each photo's
linear correction chain with a transaction advisory lock and require every
correction to supersede the effective leaf.

Keep the outcome fixed to `post_service`,
`mowing_demo_post_service_only`, `not_collected`, and `simulated`. Keep
operational approval, field evidence, execution, training, official reporting,
and field authorization false. The queue omits reviewer/device identity,
object-store coordinates, and encryption metadata.

## Consequences

- Visual outcomes are attributable, versioned, immutable, and retry-safe.
- A visible ruler does not validate a numeric height or prove vegetation
  condition, mowing, effectiveness, or completion.
- The review can gate a future simulated post-service summary without promoting
  evidence to operational or official status.
- Dashboard presentation, numeric comparison, exception review, and
  map/history updates remain separate P0 increments.
