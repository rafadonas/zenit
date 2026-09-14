# Sentinel and CBERS API guide companion

- Source: `data/raw/ZENIT_Guia_Tecnico_APIs_Sentinel_CBers.pdf`, version 1.0,
  technical validation date 2026-08-07, 38 pages
- SHA-256: `61913c6163d67e9a0e70701440b22ac0b118a2c2cd2d2ed5b1ed75aa18cf7af9`

This companion preserves the guide's architecture and scientific cautions while
distinguishing its dated provider facts and conceptual examples from current ZENIT
behavior. Provider endpoints, collections, quotas, authentication, and terms can
change and must be revalidated against official documentation before a new live or
production task.

The current implementation record is
[`docs/architecture/satellite-discovery.md`](../architecture/satellite-discovery.md).

## Architectural decision in the source

The guide recommends a provider-neutral boundary with Sentinel-2 L2A as the primary
temporal source and CBERS-4A products as complementary sources. Provider-specific
authentication, paging, collections, assets, and response metadata stay behind
adapters. Normalized observations retain provider, collection, sensor, scene ID,
acquisition time, geometry, quality, and processing version.

The source explicitly warns that NDVI expresses spectral contrast related to
vegetation vigor/cover; it does not directly measure grass height. Sentinel and CBERS
products must not be merged into one numeric series without overlap, calibration, and
field validation.

## Core concepts

- **AOI:** the road-vegetation polygon being queried, not an arbitrary broad bbox.
- **CRS:** construct metric buffers in a suitable projected CRS and transform to
  longitude/latitude for provider catalog requests.
- **STAC Collection:** a product family with common semantics.
- **STAC Item:** one acquisition/product and its metadata.
- **Asset:** a band, mask, thumbnail, XML, or raster linked to an item.
- **DN:** sensor/product digital number, requiring radiometric caution across dates.
- **Surface reflectance:** corrected product more suitable for temporal comparison.
- **COG:** GeoTIFF arranged for efficient range access where the server supports it.
- **NDVI:** `(NIR - RED) / (NIR + RED)`, subject to mask and denominator handling.

For the current study area, source and implementation use EPSG:31983 for metric work
and EPSG:4326/CRS84 for provider-facing geometry. A provider example bbox must not
replace the versioned 100 m segment-zone AOI.

## Sentinel path

The dated guide covers Sentinel Hub OAuth client credentials and four service roles:

| Service | Intended role |
| --- | --- |
| Catalog API | discover acquisitions before processing |
| Statistical API | compute time-bucketed statistics for a bounded AOI |
| Process API | produce raster/bands/index outputs for a specific request |
| broader CDSE STAC/OData/S3/OGC | optional discovery, complete-product access, or GIS integration when justified |

Client credentials are backend-only. Tokens should be reused until shortly before
expiry and never stored in Git, browser/mobile code, logs, screenshots, or responses.
OData/S3 authentication must not be confused with Sentinel Hub OAuth.

The source recommends Sentinel-2 L2A red (`B04`) and near-infrared (`B08`) at compatible
resolution for NDVI. Scene classification (`SCL`), cloud probability, and `dataMask`
support quality filtering. Tile-level cloud cover is only a prefilter; the AOI still
needs a per-pixel validity ratio.

The source's candidate mask excludes no-data, defective, shadow, water, cloud,
cirrus, and snow/ice classes and treats dark pixels experimentally. That mask is a
ZENIT engineering choice, not a provider standard or permanent scientific truth.

## Catalog, statistical, and process behavior

Catalog discovery should:

1. use a versioned AOI and UTC interval;
2. request a bounded page;
3. follow provider pagination within a task budget;
4. normalize acquisition time, footprint, cloud metadata, provider, collection, and
   scene ID;
5. preserve an immutable canonical snapshot/checksum; and
6. avoid repeating downstream work for the same provider, scene, AOI, and processor
   version.

Statistical requests should persist the interval, sample/no-data counts, valid-pixel
ratio, selected statistics/percentiles, geometry hash, source IDs, and processing
version. Empty time buckets remain empty; they must not be interpolated silently.

Process requests are appropriate for a checksummed raster used for visual inspection
or a specific derived product. A browser-ready image is not sufficient provenance:
the request, source scenes, mask, CRS, extent, processor version, checksum, and storage
role remain necessary.

## CBERS path

The guide describes the INPE Brazil Data Cube STAC catalog and two distinct CBERS-4A
families:

- WPM Level-4 DN, offering finer spatial bands but requiring local radiometric and
  quality care; and
- WFI Level-4 surface reflectance, coarser but processed for temporal analysis with
  its own masks and semantics.

The conceptual local WPM pipeline searches the catalog, selects and records item IDs,
loads red/NIR assets, aligns/reprojects them, clips to the AOI, applies available
no-data/quality rules, computes NDVI and statistics, and persists full lineage.
Panchromatic detail does not create a native 2 m NDVI because red and NIR band
resolution still controls that calculation.

WTSS can support exploratory time-series access but is not the provenance-preserving
core of ZENIT. Any token remains backend-only.

## Quality policy

Candidate metrics include:

- AOI valid-pixel ratio;
- cloud/shadow/no-data fractions;
- observation age and temporal gap;
- sample count and spatial coverage;
- sensor/product and processing level;
- geometric alignment and geometry version; and
- index distribution rather than mean alone.

Quality thresholds are versioned, configurable project rules. The current validated
Sentinel baseline is documented separately and remains prepared/inconclusive; it does
not establish an operational threshold or vegetation height.

## Reliability, quota, and security

- bound timeouts, pages, AOI, retries, and output size;
- respect provider rate-limit responses and `Retry-After` semantics;
- use exponential backoff with jitter for approved transient failures;
- make requests idempotent by provider/source/AOI/processor identity;
- cache only checksummed artifacts with source lineage;
- sanitize provider errors and never log bodies that may contain sensitive data;
- keep provider credentials in backend secret configuration; and
- expose evidence to clients through authenticated ZENIT contracts, not provider
  asset URLs.

The guide's quota and endpoint information is dated 2026-08-07. Do not encode a
historical limit as a permanent assumption.

## Current implementation reconciliation

| Guide concept | Repository state on 2026-09-13 |
| --- | --- |
| provider-neutral discovery | implemented for Sentinel, CBERS, and Planet metadata |
| Sentinel OAuth/catalog | implemented and validated against a prepared AOI |
| catalog persistence | implemented for the current satellite scene model |
| Sentinel Statistical API | one prepared real-provider validation documented |
| Sentinel Process API | small checksummed NDVI artifact and metadata documented |
| CBERS catalog | adapter and live public catalog validation documented |
| complete CBERS raster pipeline | not implemented as an operational pipeline |
| daily scheduler/queue | not implemented |
| generic raster serving | not implemented |
| Planet | discovery-only foundation added after the PDF |
| field-calibrated vegetation model | not implemented |

## Page map

| PDF pages | Content |
| ---: | --- |
| 1-4 | scope, conventions, decision, AOI/CRS/STAC/radiometry/NDVI |
| 5-7 | Copernicus service map, authentication, Sentinel-2 L2A, masks |
| 8-9 | Catalog discovery, pagination, idempotency |
| 10-13 | Process and Statistical API patterns |
| 14-15 | quality, temporal filtering, quota and rate limiting |
| 16 | CDSE STAC, OData, S3 and OGC alternatives |
| 17-22 | INPE BDC/STAC, CBERS WPM/WFI, local processing and WTSS |
| 23-26 | ZENIT AOIs, provider interface, canonical model and persistence |
| 27-30 | scheduling, risk features, ground truth, security and observability |
| 31-34 | tests, implementation plan, conceptual Java/internal API examples |
| 35-38 | production checklist, cheat sheet, glossary, references, decisions |

## Material not copied as current contract

The PDF contains example cURL, JSON, SQL, Python, Java, Evalscript, endpoints, AOIs,
dates, limits, and internal API shapes. They remain examples tied to the 2026-08-07
guide. Reuse only after checking current provider documentation, accepted ADRs,
repository code, versioned OpenAPI, and data-quality evidence.
