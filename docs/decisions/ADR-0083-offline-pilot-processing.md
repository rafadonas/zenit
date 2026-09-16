# ADR-0083: Offline processing of the 1 km pilot stretch

- Status: accepted for the academic pilot; the pilot AOI and its licence remain approvals of their own
- Date: 2026-09-15
- Ticket: PLANET-008
- Predecessors: ADR-0078, ADR-0081, ADR-0082

## Context

The project can order and cache Planet assets and prove their integrity, but no
step turns those bytes into evidence per zone. Doing it online would spend quota
again on every rerun and make results depend on provider availability. Doing it
without a cloud mask would let cloud, shadow and invalid pixels enter a
statistic that looks legitimate.

Reading a four-band GeoTIFF and its UDM2 mask by hand, without a raster library,
was judged too fragile for a result that later tickets will depend on.

## Decision

Process only from local storage. `zenit-planet-process` reads the cached
analytic and UDM2 assets, refuses to run unless the most recent
`satellite_asset_verification` for both says `verified`, and never contacts the
provider: the summary always reports `provider_calls: 0`.

Add `numpy` and `rasterio` as approved dependencies. Zones are clipped from the
raster after reprojecting the prepared EPSG:31983 geometry to the raster CRS.
Pixels count only when the UDM2 clear band marks them clear and the red plus NIR
sum is non-zero; NDVI is computed from those pixels alone.

Results reuse `analysis_run` and `vegetation_analysis` rather than a new table.
The idempotency key covers scene, zone, both asset checksums, the geometry hash
and both versions, so rerunning with identical inputs creates nothing new and a
changed asset produces a new run instead of overwriting the old one. Every row is
stored as `inconclusive`, `inspect`, `low` confidence, requiring human approval
and ineligible for official reporting, and the command refuses any zone flagged
as operational.

## Consequences

- The pilot can be reprocessed as often as needed without spending quota.
- A divergent or missing asset blocks processing instead of silently producing a
  statistic, which makes PLANET-007 a hard precondition.
- The statistic is a masked spectral summary per zone. It is not height, not a
  historical class and not an authorization, and the stored explanation says so.
- Results depend on prepared geometry derived from an estimated axis; an
  approved corridor geometry remains required before any operational reading.
- Band order assumes the PSScene `analytic_udm2` product; another bundle needs a
  new processor version.
