# ADR-0004: Estimated road axis and metric CRS

- Status: accepted with operational blocker
- Date: 2026-08-06

## Context

The supplied sources contain 30 point markers labelled km 0 through km 29, but
no official road centerline. Metric segmentation requires a projected CRS and a
continuous line. Connecting markers numerically produces a 30,854.03 m line,
while labels imply roughly 29 km plus a missing 29+300 endpoint.

Quality checks found spatially reversed labels km 2/km 3 and a maximum adjacent
marker gap of 2,034.84 m. Therefore this line cannot be considered an official or
operational representation of road stationing.

## Decision

Use EPSG:31983, SIRGAS 2000 / UTM zone 23S, for metric geometry in the pilot
area. Preserve source marker geometry in EPSG:4326.

Create a versioned candidate axis by connecting markers in numeric label order
and derive 100 m geometric segments from it for API/map development only. Label
the axis and all segments `estimated`, `needs_validation`, and
`eligible_for_operations=false`.

Do not use these segments to dispatch work, validate GPS/geofences, or report
official stationing. Operational eligibility requires a reviewed official axis
or an explicitly approved normalization method in a new version.

## Consequences

- Map and GeoJSON work can proceed without hiding the data gap.
- The current candidate has 308 full 100 m segments and one 54.03 m remainder.
- Displayed distance is along the estimated geometry, not official KM stationing.
- A future official axis must create a new candidate/version and re-associate
  derived observations with documented lineage.
