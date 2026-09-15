# ADR-0074: Versioned vegetation-cover observation contract

- Status: accepted for the academic draft API; not an operational schema
- Date: 2026-09-15
- Predecessors: ADR-0072 and ADR-0073

## Context

The taxonomy and ground-truth protocol define candidate cover labels, source
quality, GPS scope, and human review. Consumers need those dimensions as
explicit properties instead of deriving meaning from a map color or from
historical N1/N2/N3 classes. The existing `vegetation_analysis` table is an
analysis result and cannot represent a corrected, append-only cover observation
without losing provenance.

## Decision

Add `vegetation_cover_observation` in migration `0040`. Each record stores the
cover type, controlled `unknown_reason`, method (`model_estimated` or
`human_reviewed`), source reference/checksum, validity, confidence, quality,
review state, taxonomy/model versions, GPS status, data status, and a JSON
provenance object. `unknown` requires a specific reason and its own rationale.

Observations are append-only. A correction is a new row linked through
`supersedes_observation_id`; the API returns only the current row in each chain
while retaining the complete history in the database. The endpoint is
authenticated and checks that the user has a non-simulated manager or
supervisor assignment for the segment's road.

The contract keeps `eligible_for_official_reporting=false` as a database and API
invariant. It does not infer height, N1/N2/N3, current condition, urgency, or
field authorization from cover type, confidence, color, or NDVI.

## Consequences

- Web and mobile consumers receive explicit, versioned semantics and can render
  `unknown` without a color-based fallback.
- Review corrections and source lineage remain auditable without mutable rows.
- Prepared/simulated observations can exercise the contract but cannot be
  promoted to official reporting by this increment.
- A future operational schema still requires dataset, privacy, licensing, and
  specialist/data-owner gates described by GEO-004 and AI-001.
