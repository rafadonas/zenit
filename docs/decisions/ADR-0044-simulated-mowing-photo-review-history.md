# ADR-0044: Simulated mowing photo-review history projection

- Status: accepted
- Date: 2026-08-12

## Context

The authenticated post-service photo queue records visual decisions, while the
read-only rehearsal history exposes the three separate typed heights. Keeping
the projections disconnected makes it difficult to audit which returned point
has a photo awaiting review or a recorded visual decision.

## Decision

Extend `GET /v1/prepared-mowing-rehearsals` with at most three
`post_service_photo_reviews`, ordered by source point. Expose only the photo
identifier, planned-point relationship, review state, latest visual decision,
quality, ruler visibility, and timestamp. Keep the exact
`post_service`/`mowing_demo_post_service_only`/`not_collected`/`simulated`
labels and all operational, execution, training, reporting, and authorization
flags false.

Join only immutable uploaded receipts and the effective leaf of the append-only
review chain. Reject source points that do not belong to the same post-service
measurement projection, duplicate point/photo identifiers, or more than three
items. Do not expose reviewer, device, object-storage, encryption, location,
height, threshold, effectiveness, or completion claims.

## Consequences

- Managers can see measurement and visual-review completeness together.
- An accepted photo remains a visual-quality signal; it does not validate a
  numeric height or prove mowing completion.
- No migration or mutable summary table is required.
- Numeric aggregation, exception handling, map/history updates, and official
  reporting remain separate increments.
