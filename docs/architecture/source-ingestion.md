# Source ingestion architecture

## Boundary

Sprint 1 ingestion ends in staging. It does not silently promote records into
road, segment, zone, recommendation, or work-order domain tables.

```text
immutable raw file
  -> source_file identity (SHA-256)
  -> import_job (parser + version + canonical parameters)
  -> import_run (numbered execution attempt)
  -> typed parser and anomalies
  -> staging tables in EPSG:4326
  -> explicit validation/promotion in a later transaction
```

## Idempotency

The import key is SHA-256 over the source checksum, parser name, parser version,
and canonical JSON parameters. It identifies an immutable `import_job`. Each
execution is a numbered `import_run`, so retries preserve earlier failures and
their anomalies. A successful job is not executed again. Pending or running
attempts are treated as in progress. Failed or rejected attempts may be retried.

Changing source bytes, parser version, or parameters intentionally produces a
new key. Filenames and modification timestamps are not identities.

## Spatial policy

Original KML geometry is stored as PostGIS geometry with SRID 4326. No metric
distance or area is calculated in staging. A validated SIRGAS 2000 / UTM CRS is
required before derived metric geometry is created.

Invalid source polygon topology is allowed only in staging. PostGIS records an
`invalid_geometry` warning with `ST_IsValidReason`; a future normalized layer may
use a documented repair, while the original geometry remains unchanged.

The numeric value inferred as polygon area is retained as a source-attribute
interpretation with `needs_validation`; it is not recomputed or asserted as
official area.

## Transaction policy

An import adapter must:

1. insert or resolve `source_file` by checksum;
2. reserve the unique idempotency key in `import_job`;
3. lock the job and create a numbered `import_run` in a short transaction;
4. parse outside long database locks;
5. insert staging records and anomalies atomically;
6. mark the run `succeeded` only after counts and constraints pass;
7. roll back staging writes and mark the run `failed` on error.

Raw objects and successful staging rows are never updated in place. Reprocessing
uses a new parser version or parameters and creates a new import run.

## Execution

After applying `infra/migrations/0001_source_catalog_and_staging.sql`, install the
project and import one source at a time:

```bash
zenit-import km-markers "data/raw/01. Rodovia Motiva - Rodoanel/Marco km_rodoanel 2.kmz"
zenit-import mowing-polygons "data/raw/01. Rodovia Motiva - Rodoanel/classificacao_rocada.kmz"
zenit-import vegetation-workbook "data/raw/02. Dados Gestão verde - Atual/Retigrafico/RA-RET-ROÇ-LIMP-2026-03-13.xlsx"
```

The command accepts only files physically located below `data/raw/`. It does not
print credentials, change the raw file, or perform domain promotion. A parser
exception marks its numbered attempt failed; validation errors preserve anomalies
and mark the attempt rejected.
