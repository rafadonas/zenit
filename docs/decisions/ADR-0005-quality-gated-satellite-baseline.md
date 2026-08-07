# ADR-0005: Quality-gated satellite baseline

- Status: accepted
- Date: 2026-08-07

## Context

No Sentinel-2 or CBERS-4A scene has been supplied with the project. The source
set also does not establish a validated relationship between NDVI and vegetation
height. A cached image can support reproducible analysis, but its age and quality
must remain visible and it cannot be represented as a current field condition.

## Decision

Catalog every scene and asset with acquisition/cache timestamps, sensor,
checksum, quality, and data-status labels. Make processing runs idempotent and
store their rule and processor versions.

Aggregate analysis by the four required segment zones: left, right, median, and
special. General zones use the 30 cm threshold; special zones use 10 cm. Zone
geometry may remain absent and `prepared` until a validated corridor geometry is
available, and non-real zones are never operationally eligible.

The baseline treats NDVI only as a vegetation-index measurement. It does not
convert model confidence or NDVI into vegetation height. Low-quality, rejected,
insufficient-pixel, cached-preparation, or otherwise non-real inputs produce an
inconclusive result and an inspection recommendation. A mowing threshold breach
can only produce `mowing_review`, always requiring human approval; it never
authorizes field work.

## Consequences

- The catalog and rules can be developed and tested without fabricating imagery.
- A real processing run remains pending until an approved scene is available.
- Cached results retain their acquisition date and cannot silently appear current.
- Official reporting requires real height evidence and a conclusive result.
- Future raster processing must preserve these contracts and add its processor
  version and lineage rather than overwriting prior results.
