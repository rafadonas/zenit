# ADR-0067: Backend-only Planet provider foundation

- Status: accepted
- Date: 2026-09-13

## Context

The project account reports access to Planet basemap tiles, scene tiles, and a
limited scene-download area quota. Planet catalog, tile, basemap, and order APIs
have different quota and delivery semantics. Sending a Planet API key to the
dashboard would expose the account credential and allow uncontrolled quota use.

PlanetScope imagery can improve spatial detail, but it does not directly measure
vegetation height and does not distinguish grass from trees without validated
labels and ground truth.

## Decision

Add Planet as a provider-neutral `PSScene` catalog source using the Data API
quick-search endpoint and backend-only `PL_API_KEY` authentication. Normalize
scene time, footprint, fractional cloud cover, provider, sensor, and collection.
Do not expose provider asset URLs or credentials through this boundary.

The first increment is discovery-only. It does not order scenes, download
assets, proxy tiles, persist Planet scenes, or mark results as operational.
Browser tile access must later use a controlled backend proxy/cache because the
Planet key must not be present in client URLs.

## Consequences

- Offline tests can validate request construction, normalization, pagination,
  credential handling, and failure behavior.
- `zenit-planet-catalog` can validate account access without requesting a scene
  download.
- Persistence requires a separate migration extending the current database
  sensor constraint to `planet-scope`.
- Scene ordering, quota accounting, asset checksums, tile proxying, and storage
  require separate reviewed tickets before implementation.
- Planet-derived outputs remain non-operational until AOIs, licenses, quality,
  provenance, and field validation are approved.
