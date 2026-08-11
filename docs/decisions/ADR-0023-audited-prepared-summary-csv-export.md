# ADR-0023: Audited prepared-summary CSV export

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0022 provides an immutable prepared return summary, but users could only
read it in the authenticated dashboard. The P0 demonstration needs a portable
summary artifact without presenting simulated locations and prepared typed
measurements as an official operational report. Exported spreadsheet cells also
need protection against formulas in user-authored rationale or purpose text.

## Decision

Expose an authenticated CSV export only to a current non-simulated manager or
supervisor assigned to the summary's road. Require a human-entered export
purpose, a client idempotency key, and an immutable export event containing the
actor, summary, purpose, schema version, byte size, and SHA-256 checksum.
PostgreSQL repeats the active-user, road-role, simulated-location, prepared-data,
non-official, and non-authorizing gates before accepting the event.

Version the artifact as `prepared-inspection-summary-csv-v1`. Include a prominent
prepared-demo notice, summary policy version, generation rationale, three-point
counts, minimum/mean/maximum heights, N1/N2/N3 counts, class rule, timestamps,
and every safety status. Do not include actor identity, device data, photo
coordinates, or object-storage details. Prefix formula-capable user text before
CSV serialization.

The dashboard proxy enforces exact origin, CSRF, UUID and allowlisted form
fields; keeps the bearer token in the `httpOnly` cookie; verifies media type,
schema version, safety headers, one-megabyte size ceiling, and checksum; and
returns a server-named, `no-store`, `nosniff` attachment.

## Consequences

- Every successful prepared export is attributable and integrity-checkable.
- Replays with the same key and payload return identical deterministic bytes;
  conflicting reuse is rejected.
- The CSV is useful for academic review but remains explicitly unsuitable for
  official reporting, model training, or field authorization.
- Official report templates, validated GPS/measurement evidence, retention
  policy, and real operational reporting remain future, separately approved work.
