# ADR-0006: Provider-neutral satellite discovery

- Status: accepted
- Date: 2026-08-07

## Context

The satellite integration guide supplied on 2026-08-07 documents Sentinel-2
L2A through Copernicus Sentinel Hub and CBERS-4A through the INPE Brazil Data
Cube STAC API. The providers use different collections, assets, radiometric
levels, authentication mechanisms, and processing paths. Embedding those details
in analysis rules would make provenance ambiguous and future provider changes
risky.

The guide recommends operational AOIs near 1 km, but ZENIT's controlling domain
rule requires analysis by 100 m road segment and separate left, right, median,
and special zones. The supplied road axis also remains estimated and blocked for
operations.

## Decision

Introduce a provider-neutral discovery boundary that normalizes acquisition ID,
provider, collection, sensor, acquisition time, footprint/bbox, cloud metadata,
asset references, and source metadata. Keep Sentinel and CBERS observations in
separate sensor/product series; no cross-sensor NDVI equivalence is assumed.

Build provider requests from versioned 100 m `segment_zone` AOIs in EPSG:4326.
Metric AOI construction remains in EPSG:31983. The current estimated segments
may support development queries only and remain ineligible for field operations.

OAuth token handling, bounded HTTP retries, and catalog calls use the same
boundary. Credentials are backend/worker-only environment settings and must
never be returned by the API or written to logs. Idempotent database persistence
stores first-discovery metadata separately from future cached raster assets.
Provider scene identity is `(provider, external_scene_id)` and multipart
footprints remain MultiPolygon in EPSG:4326.

## Consequences

- Catalog payload construction and response normalization can be tested offline.
- Pagination and provider metadata remain explicit for later idempotent imports.
- Sentinel-2 L2A remains the primary temporal source; CBERS WPM/WFI remain
  complementary and retain their DN/SR distinction.
- NDVI remains spectral evidence and is never converted directly into height.
- Catalog discovery and persistence are validated, but discovery alone is not a
  raster or vegetation result. Raster quality checks, cached-asset checksums,
  and processing provenance remain mandatory before analysis.
