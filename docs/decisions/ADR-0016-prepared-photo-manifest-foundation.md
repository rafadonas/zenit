# ADR-0016: Prepared photo-manifest foundation

- Status: accepted
- Date: 2026-08-09

## Context

Sprint 5 requires a photo at each planned point, but the API has no object
upload boundary and the Flutter client has no reviewed capture dependency.
Persisting a filename or client claim as received photographic evidence would
break provenance and could contaminate reports or future training data.

## Decision

Accept `photo/prepare` through the existing idempotent mobile sync contract.
Store an append-only manifest with client-generated photo UUID, exact prepared
order and point, actor, device, capture time, SHA-256, byte size, and an
allowlisted image media type.

Fix every manifest to `content_status=not_uploaded`,
`ruler_status=not_validated`, `quality_status=prepared_unverified`, no collected
location, and no official-reporting or field-work eligibility. Repeat the
payload, target, authorization, and safety checks in PostgreSQL. Do not store an
object URI or claim that media content exists in this increment.

## Consequences

- Metadata retry and conflicts inherit batch/event idempotency and audit.
- A checksum is provenance for a future upload, not proof that bytes were
  received or that a ruler is visible.
- The 25 MiB limit is a tracked technical guardrail, not an official Motiva
  policy.
- Actual capture, encrypted local bytes, upload, server checksum verification,
  object versioning, retention, and photo-quality review remain required.
