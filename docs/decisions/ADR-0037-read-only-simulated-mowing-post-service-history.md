# ADR-0037: Read-only simulated mowing post-service history

- Status: accepted
- Date: 2026-08-12

## Context

ADR-0035 and ADR-0036 persist three separate simulated post-service heights,
but the authenticated management projection stops at the mowing-rehearsal
timeline. Managers therefore cannot audit the synchronized typed input without
querying storage directly. Producing a minimum, maximum, mean, class, threshold
comparison, reduction, or effectiveness result would prematurely turn
unverified demonstration input into a post-service summary.

## Decision

Extend `GET /v1/prepared-mowing-rehearsals` with the raw immutable
post-service measurements associated with each returned mowing order. Preserve
the existing road-scoped manager/supervisor access boundary and omit actor,
device, coordinates, and server-receipt details.

Return zero to three measurements ordered by their source planned-point
sequence. For every item expose the typed height, capture time, source planning
approval and planned-point identifiers, plus the exact simulated, unverified,
non-operational safety labels. Revalidate that points and event identifiers are
unique, the source order matches, the planning approval is stable, the
rehearsal is finished, and capture does not predate `finish`. Fail closed on any
promoted flag or inconsistent relationship.

Render these values beside the existing rehearsal timeline as digitized input
only. Do not calculate or display N1/N2/N3, minimum, maximum, mean, before/after
change, threshold compliance, mowing effectiveness, or official completion.

## Consequences

- Managers can audit which simulated heights were synchronized at each source
  point without exposing field-worker identity, device, or location.
- Partial sets remain visibly partial instead of being promoted to a summary.
- The projection adds no mutable summary table and requires no migration.
- Post-service photos, human review, a separately governed summary, threshold
  exceptions, map/history updates, and official reporting remain future P0 work.
