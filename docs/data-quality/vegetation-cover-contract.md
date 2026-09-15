# Contrato de observação de cobertura vegetal

Migrations `0040_vegetation_cover_contract.sql` and
`0042_vegetation_cover_contract_invariants.sql`, together with the authenticated endpoint
`GET /v1/segments/{segment_id}/vegetation-cover` expose the draft taxonomy
without presenting it as an operational decision.

## Response dimensions

Each effective observation includes:

- `cover_type`, with a required `unknown_reason` for `unknown` and an optional
  controlled reason for `mixed`;
- `cover_type_method`, source reference/checksum, and acquisition time;
- `validity_status`, `confidence_band`, and `quality_status`;
- `review_state`, taxonomy/model versions, rationale, and provenance;
- zone/segment identifiers and a GPS status restricted to `simulated` or
  `unavailable` in the current draft; and
- `data_status` plus `eligible_for_official_reporting=false`.

The API is read-only in this increment. Manager and supervisor assignments are
checked against the road and simulated assignments are denied. Invalid or
inaccessible segments do not reveal observations.

Every `model_estimated` observation requires a non-empty `model_version`. Real
GPS and device accuracy remain rejected until coordinates, timestamp, SRID,
consent reference, pseudonymized device reference, retention, and privacy rules
are approved and introduced through a later versioned migration.

## History and uncertainty

Rows are immutable. A corrected label inserts a new row that points to the row
it supersedes; the endpoint returns the latest row and the link allows an audit
consumer to follow history. `unknown` is not the same as `non_vegetation`, and
confidence or quality is not a measurement of height. Historical N1/N2/N3 and
NDVI remain independent dimensions.

The initial taxonomy remains `zenit-cover-taxonomy-v0.1-draft`. The current
demonstrator may use `prepared` or `simulated` observations only; such records
are excluded from model training and official reports.
