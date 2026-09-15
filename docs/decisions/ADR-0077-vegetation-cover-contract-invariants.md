# ADR-0077: Vegetation-cover draft contract invariants

- Status: accepted for the academic draft API; real GPS remains blocked
- Date: 2026-09-15
- Predecessor: ADR-0074

## Context

The first versioned vegetation-cover contract established an append-only schema
and an authenticated read endpoint. Review after integration identified three
states that the schema could represent even though the governing taxonomy and
ground-truth protocol do not permit them:

- a model estimate without a model version;
- mixed cover that could not retain a controlled reason such as
  `mixed_without_dominance`; and
- `gps_status=real` without the timestamp, SRID, consent reference, device
  reference, and privacy policy required by ADR-0073.

The endpoint tests also replaced the PostgreSQL reader, leaving its authorization,
current-chain selection, count, and row mapping outside direct coverage.

## Decision

Apply migration `0041` without modifying the already integrated migration
`0040`. Require a non-empty `model_version` for every `model_estimated`
observation. Require `unknown_reason` for `unknown`, permit it for `mixed`, and
reject it for the remaining cover types.

Keep the current API and database fail-closed for location: only `simulated` and
`unavailable` GPS states are exposed, and `gps_accuracy_m` remains null. A future
migration may enable `real` only after a versioned contract includes the complete
ADR-0073 metadata and the privacy, consent, retention, and device-pilot gates are
approved.

Add repository-level unit coverage and a PostgreSQL Compose smoke script that
executes the real constraints against a fresh migrated schema.

## Consequences

- Model-derived labels cannot lose their model version.
- Mixed observations preserve controlled uncertainty without being coerced to
  `unknown`.
- The draft cannot accidentally persist incomplete real-location claims.
- GEO-003 remains an academic, read-only contract and does not by itself unblock
  MOB-005, real field collection, model training, or official reporting.
