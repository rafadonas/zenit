# ADR-0003: Immutable raw data and explicit lineage

- Status: accepted
- Date: 2026-08-06

## Context

The supplied spreadsheets and KML/KMZ files contain ambiguous dates, inconsistent
attributes, and source evidence that must remain auditable. Silent corrections
would make later validation impossible.

## Decision

Treat every file under `data/raw/` or the raw object-storage bucket as immutable.
Register its SHA-256, size, media type, import time, parser version, reference
date, and validation status. Write normalized and corrected interpretations only
as versioned derived products with lineage back to the source.

Inferences, including the shifted attributes in `classificacao_rocada.kmz`, must
carry an explicit validation status and must not overwrite source values.

## Consequences

- Imports must be idempotent and content-addressed.
- Storage usage increases because raw and derived representations coexist.
- Corrections are new versions, enabling reproducible audits and rollback.
