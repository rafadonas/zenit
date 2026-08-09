# ADR-0013: Mobile persistent prepared-sync queue

- Status: accepted
- Date: 2026-08-09

## Context

ADR-0012 established the server synchronization contract but left the Flutter
drafts as `local_only`. Mobile delivery can fail after the server commits and
before the app receives the response. Generating a new batch or event ID during
retry would weaken idempotency, while deleting local events on logout or token
expiry would violate the persistent-acknowledgement rule.

## Decision

Generate RFC 4122 version-4 UUIDs locally with a cryptographically secure random
source. Protect the installation's logical `device_id` in Android secure
storage. Each of the three prepared measurement drafts receives a persistent
`event_id` before network use.

Before sending, atomically persist one pending batch containing its `batch_id`,
`device_id`, order, base cursor, and ordered event IDs, and mark the events
`pending`. Register the device, submit that exact batch, and reuse it unchanged
after transport failure or app restart. Sync payloads explicitly declare
prepared data, inspection phase, no GPS, no photo, and no official-reporting
eligibility.

Accept a server result only when it matches the pending batch, covers every
event exactly once, reports persistent acknowledgement for accepted events,
and preserves all non-operational flags. Store each result locally as
`acknowledged`, `rejected`, or `conflict`, advance the cursor, and only then
remove the pending-batch marker. Keep the measurement evidence itself locally.

Logout and token expiry remove session access but retain encrypted data and the
pending batch. A later login by the same user can resume it. A different user
cannot replace unacknowledged events; once no unacknowledged event exists, the
vault may be cleared and rebound to the new user. This supersedes ADR-0011's
initial logout behavior that discarded local drafts.

Compile the app version into the client with `ZENIT_APP_VERSION`, defaulting to
the tracked package version for local development. Do not add a package solely
to read build metadata in this P0 slice.

## Consequences

- A lost HTTP response causes safe replay of the same batch rather than a
  duplicate prepared measurement.
- Local events survive session loss until the server returns a persistent
  outcome.
- Persisted results cannot be overwritten in place; a future correction flow
  must create an explicitly related new event.
- Synchronization remains user-initiated and foreground-only. Background retry,
  connectivity scheduling, device enrollment approval, and remote revocation
  UI remain future work.
- A synchronized prepared measurement still does not prove an inspection,
  contain GPS/photo evidence, authorize field activity, or enter an official
  report.
