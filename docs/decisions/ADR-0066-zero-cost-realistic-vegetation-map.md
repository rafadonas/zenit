# ADR-0066: Zero-cost realistic vegetation map

- Status: accepted
- Date: 2026-09-10

## Context

The corridor screen used a schematic SVG that showed the candidate SP-021 axis
without surrounding roads or geographic context. The source catalog already
contains 642 mowing polygons and two historical vegetation workbooks, but the
polygon attributes have a shifted mapping and the workbook reference date is
2025-03-28. Neither source represents the current road condition.

The project has no budget for a commercial map service. Google Maps requires a
billing-enabled project and API key even when usage remains within a free
allowance.

## Decision

Use MapLibre GL JS with the standard OpenStreetMap raster layer for the local,
low-volume academic demonstration. Expose the tile URL through the dashboard's
runtime configuration, show the required OpenStreetMap attribution, allow the
browser to send an origin referrer, and do not prefetch or offer offline tile
downloads.

Expose a read-only vegetation map GeoJSON collection from the API. Preserve the
original staging polygons unchanged. For display only:

- repair invalid geometry in the query with `ST_MakeValid`;
- associate each polygon with the nearest estimated 100 m road segment;
- associate that segment with the nearest 500 m station in the newest imported
  workbook version;
- use the conservative highest N1/N2/N3 class at that station;
- retain X and unknown states as neutral map colors.

Every feature is labelled `historical`, `inferred_needs_validation`, and
ineligible for operations. The map and popup display the 2025-03-28 reference
date and state that the layer is not current.

## Consequences

- The map provides familiar roads, labels, zoom, pan, and scale at no monetary
  cost for the low-volume demonstration.
- All 642 imported polygons can be displayed without altering raw or staging
  evidence.
- The map does not claim nationwide monitored coverage: OpenStreetMap shows the
  surrounding road network, while ZENIT overlays only imported monitored data.
- The inferred polygon-to-class relationship must be replaced by validated zone
  geometry and current measurements before operational use.
- Public or high-volume hosting must use a policy-compliant hosted or self-hosted
  tile service rather than relying on the community server without an SLA.
