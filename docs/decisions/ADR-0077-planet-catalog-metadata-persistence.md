# ADR-0077: Persist Planet catalog metadata

- Status: accepted for bounded, non-operational metadata
- Date: 2026-09-15
- Ticket: PLANET-003
- Predecessors: ADR-0067, ADR-0075, ADR-0076

## Context

The account and scene-level permission checks now work, but catalog responses
are not yet reproducible after the process exits. The existing idempotent
satellite catalog table can retain normalized scene metadata and a checksum, but
its sensor constraint predates PlanetScope.

## Decision

Migration `0041` extends `satellite_scene.sensor` with `planet-scope` while
keeping the product series distinct from Sentinel and CBERS. The new
`zenit-planet-persist` command searches a bounded AOI/time window with the
`assets:download` permission filter and writes normalized scenes through the
existing `(provider, external_scene_id)` idempotent catalog. `--persist` is a
required explicit confirmation.

Persisted rows remain catalog metadata only: `cache_status=discovered`, no asset
bytes, no Order, and no operational eligibility. The reversible migration refuses
to remove Planet support while Planet rows exist, preventing silent data loss.

The bounded validation on 2026-09-15 persisted 13 scenes on its first run and
returned 13 existing scenes on an immediate repeat. The database contains 13
`planet-scope` rows with `cache_status=discovered`, `cached_at=NULL`, and catalog
checksums; no asset bytes were written.

## Consequences

- Repeating the same bounded search creates zero duplicate scenes and preserves
  the first catalog snapshot/checksum.
- Scene metadata can be joined by a later quality/processing ticket without
  pretending that a catalog item is a cached raster or vegetation measurement.
- Product bundle, license, area quota, Order, download bytes, checksum of each
  asset, and human approval remain required before acquisition.
