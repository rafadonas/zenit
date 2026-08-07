# PostGIS import validation

Date: 2026-08-06

Environment: local development, Docker rootless
Database image: `postgis/postgis:17-3.5`

## Applied migrations

- `0001_source_catalog_and_staging.sql`
- `0002_allow_invalid_staging_polygons.sql`

Both migrations completed with `ON_ERROR_STOP=1`. PostGIS and pgcrypto are
enabled. Original KML geometries are stored with SRID 4326.

## Import results

| Entity | Rows |
| --- | ---: |
| Source files | 4 |
| Import jobs | 4 |
| Import attempts | 5 |
| Kilometer markers | 30 |
| Mowing polygons | 642 |
| Vegetation observations | 960 |
| Structured anomalies | 16 |

The four sources are the two KML/KMZ files and two XLSX versions. Contract and
challenge documents are catalogued in the filesystem audit but are not staging
inputs for these structured parsers.

## Attempts and idempotency

- KM markers: attempt 1 succeeded with 30 rows and one source-order warning.
- Mowing polygons: attempt 1 failed on the original strict topology constraint.
- Migration 0002 corrected staging policy to preserve invalid source evidence.
- Mowing polygons: attempt 2 succeeded with 642 rows and 15 warnings.
- Both vegetation workbooks: attempt 1 succeeded with 480 rows each.
- Re-importing the marker file returned `already_succeeded`; no duplicate run or
  staging rows were created.

The failed polygon attempt remains in `import_run`, demonstrating that retries do
not erase operational history.

## Anomalies

| Code | Severity | Count |
| --- | --- | ---: |
| `extension_content_mismatch` | warning | 1 |
| `invalid_geometry` | warning | 13 |
| `non_sequential_source_order` | warning | 1 |
| `shifted_attribute_mapping` | warning | 1 |

All 13 invalid geometries are self-intersections reported by PostGIS. No repair
was applied to staging geometry.

## Classification totals

Across both document versions:

| Class | Rows |
| --- | ---: |
| N1 | 342 |
| N2 | 105 |
| N3 | 49 |
| X / not applicable | 464 |

These are versioned historical observations with reference date 2025-03-28, not
the current condition of the roadway and not a temporal growth series.
