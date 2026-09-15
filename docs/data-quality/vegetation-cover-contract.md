# Contrato de observação de cobertura vegetal

Migration `0040_vegetation_cover_contract.sql` and the authenticated endpoint
`GET /v1/segments/{segment_id}/vegetation-cover` expose the draft taxonomy
without presenting it as an operational decision.

## Response dimensions

Each effective observation includes:

- `cover_type` and a required `unknown_reason` when the value is `unknown`;
- `cover_type_method`, source reference/checksum, and acquisition time;
- `validity_status`, `confidence_band`, and `quality_status`;
- `review_state`, taxonomy/model versions, rationale, and provenance;
- zone/segment identifiers and GPS status/accuracy when available; and
- `data_status` plus `eligible_for_official_reporting=false`.

The API is read-only in this increment. Manager and supervisor assignments are
checked against the road and simulated assignments are denied. Invalid or
inaccessible segments do not reveal observations.

## History and uncertainty

Rows are immutable. A corrected label inserts a new row that points to the row
it supersedes; the endpoint returns the latest row and the link allows an audit
consumer to follow history. `unknown` is not the same as `non_vegetation`, and
confidence or quality is not a measurement of height. Historical N1/N2/N3 and
NDVI remain independent dimensions.

The initial taxonomy remains `zenit-cover-taxonomy-v0.1-draft`. The current
demonstrator may use `prepared` or `simulated` observations only; such records
are excluded from model training and official reports.
