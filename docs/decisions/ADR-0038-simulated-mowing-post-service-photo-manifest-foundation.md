# ADR-0038: Simulated mowing post-service photo-manifest foundation

- Status: accepted
- Date: 2026-08-12

## Context

Inspection photos are bound to inspection work orders and the `inspection`
phase. Reusing that contract after a mowing rehearsal would erase the evidence
phase and provenance boundary. Post-service image bytes also cannot be called
uploaded or reviewed merely because a mobile client calculated a checksum.

## Decision

Add a separate `mowing_photo/prepare` sync event and persist its append-only
manifest in `prepared_mowing_post_service_photo_manifest`. Bind it to the
prepared mowing order, effective planning approval, source planned point, and
the already persisted separate post-service measurement for that point.

Require capture at or after the measurement timestamp, one immutable manifest
per mowing-order/point pair, a globally unused photo UUID, a lowercase SHA-256,
an allowlisted JPEG/PNG type, and a tracked 25 MiB technical limit. Fix the
contract to `post_service`, `mowing_demo_post_service_only`, `not_uploaded`,
`not_validated`, `not_collected`, `simulated`, and
`simulated_unverified`. Keep all approval, execution, training, and official
reporting flags false.

Repeat the exact accepted-event, point ownership, planning provenance, active
actor/device, road-role, timestamp, and non-operational checks in PostgreSQL.
Do not accept image bytes or create an upload receipt in this increment.

## Consequences

- Post-service photo metadata remains separate from inspection evidence.
- A checksum and manifest prove neither server possession nor image quality,
  ruler visibility, vegetation condition, mowing execution, or completion.
- Retries and conflicts use the existing persistent event/batch audit trail.
- Encrypted mobile capture, verified encrypted upload, authorized retrieval,
  human review, summary use, and retention remain separate P0 increments.
