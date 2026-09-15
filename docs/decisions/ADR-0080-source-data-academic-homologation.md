# ADR-0080: Homologação acadêmica controlada dos dados de origem

- Status: accepted for the academic prototype; operational validation remains blocked
- Date: 2026-09-15
- Ticket: GOV-003
- Data owner: Rafael (project owner)
- Predecessors: ADR-0004, ADR-0002, ADR-0073

## Context

The ZENIT source package contains a candidate SP021 axis, mowing-classification
polygons, and two historical workbook versions. The files are useful for
reproducible development, but they do not establish the official road axis,
stationing, zone boundaries, current condition, or an operational mowing
decision. The polygon file also has a misleading `.kmz` extension and an
inferred attribute mapping that requires validation.

The project owner confirmed the academic scope and the following safeguards:
the four analysis zones remain independent; inferred values remain explicit;
the reference date is preserved; and no output based on these sources may be
used as an operational situation, official report, or silent mowing
authorization.

## Decision

Accept the source package for the academic prototype under review identifier
`zenit-source-review-2026-09-15` and the machine-readable manifest
`data/manifests/source-homologation-2026-09-15.json`.

The review establishes these controlled interpretations:

- The marker source describes `SP021` km 0 through km 29 as 30 Point features
  in WGS 84 (`EPSG:4326`). Metric derivations may use SIRGAS 2000 / UTM zone
  23S (`EPSG:31983`) only as an explicitly versioned processing CRS.
- The candidate axis and all derived segments/zones remain `estimated` and
  `needs_validation`. The four ZENIT zones (`left`, `right`, `median`, and
  `special`) are evaluated separately, but the source package does not prove
  their official boundaries.
- The 642 mowing polygons retain their original geometry and equipment-like
  `name` values. The observed shifted mapping (`classe` as latitude-like,
  `KM` as longitude-like, and `Latitude` as area-like) is an inference with
  `inference_status=needs_validation`, never an official attribute mapping.
- The two workbooks retain distinct document-version labels. Their internal
  serial date `45744` is recorded as the reference date `2025-03-28`; the
  filename dates are not treated as survey dates or vegetation growth.

No raw file is renamed, repaired, overwritten, or promoted by this decision.
Derived data may be written only to staging, `data/processed/`, or approved
object storage with checksum and lineage.

## Exceptions and release gates

The following remain visible and block operational promotion: reversed or
non-uniform marker spacing (including the km 2/km 3 ordering), the missing
29+300 marker, 13 self-intersecting source polygons, the false KMZ extension,
the shifted polygon fields, missing category descriptions for some kilometer
values, absent official axis/zone boundaries, and the lack of an authoritative
survey date. A future source version or owner decision must resolve these
exceptions before promotion.

The review therefore sets `eligible_for_operations=false`,
`eligible_for_official_reporting=false`, and `eligible_for_model_training=false`
for records derived from this package. It does not approve real GPS collection,
specialist validation, or a production identity/policy.

## Consequences

- Developers can use a stable, checksummed source review for the prepared
  demonstrator without presenting it as current roadway truth.
- Importers and consumers must preserve `estimated`, `prepared`, and
  `needs_validation` labels and keep source lineage attached.
- GEO-004 and AI-001 remain gated on a separate licensed, adjudicated dataset;
  this academic review does not make demo or simulated data eligible for
  training.
- An official axis, zone geometry, attribute mapping, and date relationship
  require a new versioned review and explicit owner approval.
