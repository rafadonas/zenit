# ADR-0002: PostgreSQL/PostGIS as transactional and spatial source of truth

- Status: accepted
- Date: 2026-08-06

## Context

ZENIT must connect road geometry, 100 m segments, analysis zones, observations,
recommendations, approvals, work orders, and field evidence with transactional
integrity and spatial queries.

## Decision

Use PostgreSQL with PostGIS as the authoritative transactional and spatial
database. Store large source files, raster products, and field media in object
storage; store immutable identifiers, metadata, checksums, provenance, and object
references in PostgreSQL.

Every persisted geometry must have an explicit SRID. Metric calculations must use
a validated projected SIRGAS 2000 / UTM CRS, while original KML coordinates remain
preserved in EPSG:4326.

## Consequences

- Spatial and operational state can be queried consistently.
- Schema changes require reviewed migrations and spatial constraints/indexes.
- Database backups alone do not restore object data; object-storage continuity
  and referential validation are also required.
