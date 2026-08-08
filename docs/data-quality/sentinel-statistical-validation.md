# Sentinel Statistical API technical validation

Date: 2026-08-07

Status: real provider response over a prepared, non-operational AOI

## Scope

This validation exercised Copernicus OAuth, Sentinel Hub Statistical API,
Sentinel-2 L2A reflectance, SCL/dataMask filtering, NDVI statistics, quality
gating, and idempotent PostGIS persistence. It did not validate roadway
stationing, right-of-way geometry, vegetation height, or mowing need.

The AOI was derived from estimated road segment index 195, which is a geometric
100 m development segment rather than official kilometer stationing. A 20 m
single-sided left buffer was used solely to obtain enough 10 m pixels for the API
test. The width is a configurable development parameter, is not an official
Motiva value, and must not be treated as right-of-way geometry.

Four `segment_zone` records were created to preserve the required zone model:
left and right contain prepared buffer geometry; median and special remain null
because no reliable geometry was supplied. Every zone is `prepared` and
`eligible_for_operations=false`.

## Observed result

| Field | Value |
| --- | --- |
| Sensor/product | Sentinel-2 L2A |
| Acquisition date | 2026-07-29 |
| Tile cloud-cover prefilter | 1.51% |
| Zone | left |
| Pixel resolution | 10 m |
| SCL-invalid classes | 0, 1, 3, 6, 7, 8, 9, 10, 11 |
| Valid-pixel ratio inside AOI | 100.00% |
| Pixel-quality status | accepted |
| Mean NDVI | 0.097354 |
| Domain conclusion | inconclusive |
| Recommendation | inspect |
| Confidence | low |
| Human approval required | yes |
| Eligible for official reporting | no |

`accepted` describes only pixel validity under the current configurable quality
policy. It does not mean that the AOI is official, that NDVI measures vegetation
height, or that the result is operationally reliable. The low mean may reflect a
mixture of pavement, bare soil, and vegetation caused by the estimated
centerline-derived AOI; no causal interpretation is made.

## Provenance and persistence

- Processor version: `sentinel-ndvi-scl-v1`.
- Quality rule version: `satellite-quality-2026-08-07.1`.
- The AOI geometry has a SHA-256 hash in the run parameters/explanation.
- The catalog scene remains `cache_status=discovered` and `cached_at=NULL`.
- The Statistical API may mosaic eligible inputs in the acquisition-day window;
  the linked catalog scene is explicitly labelled a prefilter candidate, not a
  claim that it was the sole contributing raster.
- Reprocessing identity includes scene, segment zone, geometry hash, interval,
  processor version, and rule version.

## Cached Process API evidence

A follow-up Process API request generated a 10 m NDVI GeoTIFF crop for the same
prepared AOI. EPSG:31983 remains the authoritative metric geometry in PostGIS;
the request geometry was transformed to provider-supported EPSG:3857 only for
processing.

- GeoTIFF dimensions: 5 × 11 pixels, Float32, Deflate-compressed.
- GeoTIFF size: 672 bytes.
- GeoTIFF SHA-256:
  `49a56d955b5f47cfb1c009004a0ab7f0515644961f108f7b8a7bac083ccd76dc`.
- `userdata.json` SHA-256:
  `0f0fff226c03d496fabf5efec1b7972d313167287f18e6dba930aedb97c33f12`.
- Provider metadata records two contributing entries with product and tile IDs.
- Both files are under ignored `data/processed/` storage and registered in
  `satellite_asset` with lineage to the catalog scene.
- The scene is `partially_cached`, not `cached`, because only the AOI crop and
  processing metadata are local; the complete source product was not downloaded.

This evidence improves reproducibility but does not make the prepared AOI or its
NDVI an operational vegetation assessment.

## Required before operational use

1. Obtain and validate an official road axis and right-of-way/zone geometries.
2. Cache and checksum the actual contributing raster assets or preserve exact
   provider source-item provenance.
3. Validate the SCL policy and AOI pixel sufficiency across representative
   corridor conditions.
4. Collect contemporaneous field photos and height measurements.
5. Calibrate any relationship between spectral features and intervention risk;
   NDVI must never be converted directly into height.
