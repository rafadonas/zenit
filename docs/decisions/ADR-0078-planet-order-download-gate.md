# ADR-0078: Planet Order and download gate

- Status: accepted for one bounded academic pilot
- Date: 2026-09-15
- Ticket: PLANET-004
- Predecessors: ADR-0067, ADR-0075, ADR-0076, ADR-0077

## Context

The account can discover and persist 13 PlanetScope catalog scenes in the
prepared development corridor, and those scenes advertise `assets:download`.
Planet Orders still have product-bundle, delivery, area quota, licensing, and
cost semantics that are not established by a catalog search. Creating an Order
is an external write and may consume the shared account quota.

## Approved pilot gate

The project owner confirmed the following reviewed manifest for this pilot:

1. one download-permitted scene selected from the prepared `SP021` segment 195
   search, with the lowest available cloud cover;
2. `analytic_udm2`, yielding `ortho_analytic_4b`, its XML metadata, and
   `ortho_udm2`;
3. the buffered 100 m segment AOI, capped at 10,000 m² and 100 MiB;
4. academic-only use, 30-day retention, and encrypted local `zenit-raw`
   storage with SHA-256 checksums and order lineage; and
5. explicit approval to create exactly one external Order, with no paid
   acquisition permitted.

The worker refuses a missing `--execute` confirmation, a larger AOI or byte cap,
an unprepared/operational segment, a second request checksum, or any result that
does not contain the complete bundle. It never prints signed links or stores
provider credentials.

## Planned safe workflow

The implementation validates the selected item and permission filter, creates
one bounded Order, polls its status with a timeout, downloads only the approved
assets, encrypts them in the local object store, verifies SHA-256 checksums, and
persists an immutable event trail with provider, item, bundle, AOI, license,
quota limits, timestamps, and lineage. A failed/partial Order remains visible
and retryable without duplicating the request.

Even a successful download remains `real` provider evidence requiring quality
checks; it does not measure height, create a vegetation label, authorize mowing,
or make the estimated road axis operational.
