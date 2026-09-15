# Satellite acquisition discovery

## Boundary

Sprint 3 discovery uses a provider-neutral boundary. Provider-specific collection
names, authentication, pagination, assets, and response metadata remain inside
the geospatial worker. The analysis domain receives normalized acquisitions and
must retain provider, collection, sensor, scene ID, and acquisition time.

```text
versioned 100 m segment-zone AOI (EPSG:4326)
  -> provider request builder
  -> bounded HTTP transport
  -> provider response parser
  -> normalized acquisition metadata
  -> idempotent catalog persistence
  -> quality validation and asset caching (next increment)
```

Metric AOIs must be constructed in EPSG:31983 and transformed to EPSG:4326 for
catalog requests. The current marker-derived axis remains estimated and cannot
be used for operational dispatch.

## Providers

- Sentinel-2 L2A: authenticated Sentinel Hub Catalog API, primary temporal
  source. OAuth uses backend-only client credentials and a thread-safe token
  cache with early renewal.
- CBERS-4A WPM/WFI: public INPE BDC STAC search, complementary source. A BDC
  access token is optional and is sent only when configured.
- PlanetScope PSScene: authenticated Planet Data API quick search, optional
  high-resolution source. The current integration discovers metadata only and
  never orders or downloads an asset.

Sentinel and CBERS observations are separate product series. WPM Digital Number,
WFI Surface Reflectance, and Sentinel L2A reflectance must not be treated as
interchangeable measurements.

PlanetScope is also a separate product series. Planet `cloud_cover` is a fraction
and is normalized to percent at the provider boundary. Scene asset URLs are not
retained by discovery because access and quota must be controlled explicitly.
The API key is sent only in a backend `Authorization: api-key ...` header; it is
never placed in a browser-facing tile URL.

## Planet foundation status

- `PL_API_KEY` is loaded as a secret from the backend environment.
- `zenit-planet-catalog` performs bounded PSScene metadata discovery for a bbox
  and UTC date window without requesting downloads.
- Offline fixtures cover AOI/date filters, fractional cloud normalization,
  pagination host validation, and credential isolation.
- Planet persistence is intentionally disabled until a migration extends the
  current `satellite_scene.sensor` constraint to `planet-scope`.
- Orders API, scene downloads, basemap discovery, tile proxy/cache, quota ledger,
  raster checksums, and processing provenance remain future reviewed increments.

`PLANET-002` adds an opt-in `assets:download` permission filter to the bounded
catalog request and exposes it through `zenit-planet-capabilities`. This checks
scene-level catalog permission only; it still does not select a product bundle,
create an Order, download bytes, or consume scene-download quota.

`PLANET-003` adds the reversible `0041` migration and
`zenit-planet-persist`. It stores only normalized, checksummed catalog metadata
with `cache_status=discovered` and idempotent provider/scene identity. The
command requires `--persist`, never stores asset bytes, and remains
non-operational. A bounded validation on 2026-09-15 persisted 13 scenes on the
first run and 13 existing scenes on an immediate repeat; all 13 remain
`cached_at=NULL`.

`PLANET-004` remains blocked until the owner records the exact scene IDs,
product bundle/assets, clipped AOI, area/byte or cost budget, academic license,
retention/destination, and explicit approval to create an external Order. A
catalog key and `assets:download` result do not satisfy those gates.

### PLANET-001 validation

On 2026-09-15 the backend-only catalog flow successfully authenticated against
the configured account for the documented development corridor AOI
`[-46.80, -23.55, -46.76, -23.50]` and UTC window `2026-08-01` through
`2026-08-07`. The `PSScene` search returned 13 acquisitions and no next page.
This confirms catalog access only; it did not request an Order, download bytes,
consume scene-download quota, or authorize an operational result. See
[`ADR-0075`](../decisions/ADR-0075-planet-account-catalog-validation.md) and the
[validation record](../data-quality/planet-account-catalog-validation-2026-09-15.md).

## HTTP safety

The standard-library transport applies timeouts and bounded retry to HTTP 429,
selected 5xx responses, and transient network errors. Sentinel Hub
`Retry-After` is interpreted as milliseconds. Error messages contain only a
status category; provider response bodies, authorization headers, client
credentials, and tokens are never included.

Tokens are reused until shortly before expiry. They are not persisted, returned
by the ZENIT API, or logged. Browser and mobile clients never receive provider
credentials.

## Current validation status

- Offline fixtures validate request construction, pagination, metadata parsing,
  token caching, retry behavior, and sanitized failures.
- A live public CBERS WPM catalog search succeeded on 2026-08-07 for the
  development corridor bbox and a 2025-01-01 through 2026-08-08 search window.
  The limited response contained five acquisitions and a next page.
- Live Copernicus OAuth and Sentinel Hub Catalog validation succeeded on
  2026-08-07 for the development corridor bbox and a 2026-07-01 through
  2026-08-08 search window. The limited response contained five acquisitions,
  cloud-cover metadata for all five, and a next-page token.
- The five Sentinel acquisitions were registered in local PostGIS and repeated
  discovery created zero duplicates. All rows are `cache_status=discovered`,
  have `cached_at=NULL`, retain valid EPSG:4326 MultiPolygon footprints, and have
  a SHA-256 catalog checksum.
- No scene asset has been downloaded, cached, quality-approved, analyzed, or
  presented as current vegetation condition.

## Persistence semantics

`satellite_scene` distinguishes provider discovery from locally cached raster
assets. `discovered_at` records the first successful catalog registration;
`cached_at` remains null until bytes are actually stored and checksummed.
`cache_status=discovered` therefore cannot be presented as a cached scene.

Registration is keyed by `(provider, external_scene_id)`. Repeating the same
catalog response returns the existing UUID and does not overwrite its first
catalog snapshot. The canonical normalized snapshot receives a SHA-256 checksum.
Provider footprints are stored as MultiPolygon in EPSG:4326 so multipart source
geometry is not simplified or discarded.

The first Statistical API validation is documented in
`docs/data-quality/sentinel-statistical-validation.md`. Its accepted pixel mask
does not override the prepared AOI status: the persisted domain result remains
inconclusive and recommends inspection.

The subsequent Process API validation stores a small checksummed NDVI GeoTIFF
and provider `userdata.json`. Cache state is `partially_cached`; only a complete
source product may use `cached`. Contributor product/tile metadata is preserved
without putting imagery in Git.

## Read-only observation contract

`GET /v1/segments/{segment_id}/satellite-observations` exposes persisted
observations for audit and review. Each item includes the provider, collection,
acquisition time, scene/zone status, quality metrics, conclusion,
recommendation, confidence band, human-approval and official-reporting gates,
rule/processor versions, explanation, and artifact role/type/checksum.

The contract does not expose storage URIs, provider response bodies, tokens, or
credentials. Its warning states that satellite quality is neither vegetation
height nor mowing authorization. Results are ordered newest first and the
bounded `limit` parameter accepts 1 through 100 items.

The dashboard has one checksum-bound visualization for the validated 5 by 11
NDVI crop. It activates only for the exact persisted artifact and preserves the
prepared, inconclusive, non-official gates. This is a derived fixed preview,
not a generic raster-serving API or evidence that a complete scene is cached;
see `docs/decisions/ADR-0033-checksum-bound-cached-ndvi-dashboard-layer.md`.

## Reproducible command

The prepared development flow is available as one idempotent command:

```bash
zenit-satellite \
  --segment-index 195 \
  --zone left \
  --from-date 2026-07-01 \
  --to-date 2026-08-07
```

The command only accepts left/right zones that already have prepared geometry,
are explicitly non-operational, and belong to the requested 100 m segment. It
discovers up to five acquisitions, chooses the lowest tile-cloud candidate,
persists catalog metadata, runs SCL-gated statistics, stores an inconclusive
inspection result, and caches the small Process API crop. Its output contains
counts and safety status only, never credentials, tokens, scene IDs, or response
bodies.
