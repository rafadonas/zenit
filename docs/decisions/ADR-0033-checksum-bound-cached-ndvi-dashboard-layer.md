# ADR-0033: Checksum-bound cached NDVI dashboard layer

- Status: accepted
- Date: 2026-08-11

## Context

The corridor dashboard exposes persisted satellite statistics and artifact
checksums, but it did not visualize raster pixels. The only local raster
evidence is a checksummed 5 by 11 Sentinel-2 NDVI crop over a prepared,
estimated AOI. The complete source scene and a true-color composition are not
cached.

A generic asset renderer would require storage authorization, media conversion,
and broader raster contracts that this P0 increment does not yet have. Showing
an unverified or merely discovered asset would also create a misleading claim
of available imagery.

## Decision

Generate a small versioned dashboard-layer contract from the existing GeoTIFF.
The generator verifies the source raster and provider-metadata SHA-256 values,
reads the Float32 pixels and georeferencing, converts the EPSG:3857 extent to
EPSG:4326, and records the derived artifact checksum and lineage. The ignored
source raster remains outside Git.

Offer the layer only when the selected persisted observation is Sentinel-2,
`partially_cached`, real at scene level, prepared at zone level,
`inconclusive`, recommends inspection, is blocked from official reporting, and
contains the exact NDVI GeoTIFF checksum and expected asset role. Switching
segment or observation disables the layer.

Render the georeferenced cells beneath the candidate road line and provide a
larger inset because a roughly 50 by 110 metre crop is too small to inspect at
the full-corridor scale. Label both views as prepared and non-operational. The
palette remains descriptive and does not create vegetation-height or mowing
classes.

## Consequences

- The validated cached NDVI evidence is inspectable in the main dashboard.
- A discovered scene, different checksum, unsafe status, or official-reporting
  promotion cannot activate this fixed preview.
- Pixel values and derived bounds are reproducible without committing the
  source GeoTIFF or exposing its storage URI.
- Generic raster serving, true-color/NIR layers, temporal comparison, and
  operational imagery remain future work.
