# ADR-0012: Prepared mobile synchronization foundation

- Status: accepted
- Date: 2026-08-09

## Context

ADR-0011 created encrypted local measurement drafts but deliberately omitted
server synchronization. The master mobile contract requires client-generated
event IDs, idempotent batches, persistent acknowledgements, device binding,
server and client timestamps, and explicit conflict preservation. The only
available orders remain prepared and non-operational under ADR-0010, so a
general work-order event API would incorrectly imply that an order can be
started or completed in the field.

## Decision

Introduce an authenticated prepared-sync boundary at `POST /v1/sync/batch` and
device registration at `POST /v1/mobile/devices`. A client-generated UUID is
bound to the authenticated user. Registrations are immutable; a separate
append-only revocation table makes later remote revocation possible without
rewriting registration evidence.

Accept batches containing one to one hundred uniquely identified events. Store
the canonical request hash, exact response, base cursor, server cursor, actor,
device, and receive time. Replaying the same `batch_id` with identical content
returns the persisted response; different content is a conflict. Replaying an
existing `event_id` with identical content is an idempotent acknowledgement.
The event hash binds content, actor, and device. Reusing the ID with different
content or identity stores both payloads and hashes in an append-only conflict
record. Device ownership and revocation are rechecked before batch replay.

For this increment, accept only `measurement/create` with phase `inspection`,
height from 0 through 1000 cm, timezone-aware client capture time, and explicit
`prepared`, no-location, no-photo, and non-official labels. Persist it as a
`prepared_field_measurement` with server receive time and
`prepared_unverified` quality. The database repeats the actor/device/road,
point/order, event/payload, and non-operational checks.

Persist unsupported events, including `work_order/start`, as rejected sync
events. They do not mutate the immutable prepared order. Every batch and
measurement remains fixed to `authorizes_field_work=false` and
`eligible_for_official_reporting=false`.

Use the project's established `/v1` route prefix rather than introducing a
second `/api/v1` namespace. The application is not wired to this contract in
this increment; local drafts therefore remain `local_only` until a subsequent
mobile change receives and persists an acknowledgement.

## Consequences

- Duplicate delivery cannot duplicate a prepared measurement.
- Batch-ID and event-ID content changes are distinguishable and auditable.
- Rejected events are evidence and cannot be silently discarded server-side.
- The cursor is a server synchronization cursor, not an offline entity ID.
- Device registration does not yet provide a user-facing enrollment approval
  or revocation endpoint; production device trust remains incomplete.
- This foundation does not start, pause, finish, or authorize a work order and
  does not claim that a measurement has GPS or photographic evidence.
- The next mobile increment can queue three UUID events, register its device,
  submit a batch, and retain each local event until its persisted result is
  recorded.
