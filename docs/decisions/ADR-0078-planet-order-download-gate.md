# ADR-0078: Planet Order and download gate

- Status: proposed and blocked on project-owner inputs
- Date: 2026-09-15
- Ticket: PLANET-004
- Predecessors: ADR-0067, ADR-0075, ADR-0076, ADR-0077

## Context

The account can discover and persist 13 PlanetScope catalog scenes in the
prepared development corridor, and those scenes advertise `assets:download`.
Planet Orders still have product-bundle, delivery, area quota, licensing, and
cost semantics that are not established by a catalog search. Creating an Order
is an external write and may consume the shared account quota.

## Gate before implementation

The project owner must record, in the ticket and a reviewed manifest:

1. the exact catalog scene(s) and product bundle/assets to request;
2. the clipped AOI and maximum area/byte or cost budget;
3. the academic license/consent and retention scope for downloaded bytes;
4. the destination bucket/prefix, encryption, checksum and lineage policy; and
5. explicit approval to create the Order in the shared Planet account.

Until these values exist, the worker may only build a dry-run payload and report
that no Order/download was requested. It must not guess a bundle, fetch a
download token, or mark any result operational.

## Planned safe workflow

After the gate is recorded, a separate implementation should validate the
selected item IDs and permission filter, create one bounded Order, poll its
status with a timeout, download only the approved asset, stream it to the
encrypted object store, verify a SHA-256 checksum, and persist an immutable
manifest with provider, item, bundle, AOI, license, quota, timestamps and
lineage. A failed/partial Order must remain visible and retryable without
duplicating the request.

Even a successful download remains `real` provider evidence requiring quality
checks; it does not measure height, create a vegetation label, authorize mowing,
or make the estimated road axis operational.
