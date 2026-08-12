# ADR-0036: Mobile simulated mowing post-service measurements

- Status: accepted
- Date: 2026-08-12

## Context

ADR-0035 added a server boundary for separate simulated post-service heights,
but the mobile app still stops at the terminal mowing-rehearsal event. Reusing
inspection drafts would erase the before/after boundary, while requiring the
device to be online immediately after `finish` would break the offline-first
demonstration flow.

## Decision

Store exactly three separate post-service drafts in the encrypted mobile vault,
one for each planned point from the source inspection order. Allow capture only
after a complete local or persistently acknowledged mowing rehearsal. Require
the capture time to be at or after the terminal rehearsal time and preserve
client-generated event UUIDs across retries. Retain the linked inspection-order
snapshot while any mowing lifecycle or measurement remains unacknowledged so a
session refresh cannot remove the point provenance required for retry.

When the rehearsal is still local, synchronize its ordered events first and the
three measurements after `finish` in one idempotent batch. PostgreSQL therefore
observes the accepted terminal event before validating the measurements in the
same transaction. When the rehearsal was already acknowledged, send only the
three new measurement events.

Fix every draft to `post_service`, `mowing_demo_post_service_only`, `simulated`,
and `simulated_unverified`, with location and photo explicitly not collected.
Keep operational approval, field authorization, execution eligibility,
model-training eligibility, and official-reporting eligibility false. Fail
closed on missing source points, stale planning provenance, mixed lifecycle
outcomes, invalid timestamps, incomplete point sets, or promoted flags.

## Consequences

- The rehearsal and its three simulated post-service heights can be completed
  offline and retried with stable identifiers.
- Previously acknowledged rehearsals can add their separate measurements
  without resending terminal lifecycle events.
- The heights remain unverified typed demo input and do not prove mowing,
  location, photo evidence, operational completion, or vegetation condition.
- Post-service photos, human review, threshold exceptions, summary projection,
  and map/history updates remain separate P0 increments.
