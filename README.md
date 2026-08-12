# ZENIT

ZENIT is a road-vegetation monitoring platform designed to connect geospatial
and satellite data with explainable recommendations, human approval, field
execution, and auditable operational reporting.

## Current status

Sprints 0–2 are complete. The repository currently provides:

- a Docker Compose development stack with Next.js, FastAPI, PostGIS, and MinIO;
- immutable source cataloguing, checksums, lineage, and idempotent imports;
- typed KMZ/KML and workbook parsers with structured anomaly reporting;
- a marker-derived candidate axis split into 309 geometric segments;
- a bbox GeoJSON endpoint and a read-only Next.js corridor dashboard; and
- Python and TypeScript lint, tests, builds, and CI gates.

The candidate axis is development-only. It is explicitly labelled `estimated`,
`needs_validation`, and `eligible_for_operations=false` because no official road
axis was supplied and the marker dataset contains known inversions and gaps.

Sprint 3 is in progress. Its database foundation now catalogs cached satellite
scenes and checksummed assets, versioned/idempotent runs, segment zones, quality
metrics, and explainable recommendations. A non-persisting analysis preview is
available for validating the baseline rules. Discovery adapters normalize
Sentinel Hub Catalog and INPE BDC STAC acquisitions without exposing provider
details to the analysis domain. A public CBERS catalog query has been validated,
and Copernicus OAuth plus Sentinel-2 catalog discovery have also been validated
with a limited live query. Five Sentinel acquisitions are persisted idempotently
as catalog-only `discovered` metadata. No scene asset has been downloaded or
approved for operational use. A Statistical API validation over one prepared
100 m AOI passed pixel-quality checks but is persisted as inconclusive/inspection
because the axis and buffer are not official and NDVI is not height. No current
vegetation or mowing result is claimed. A 5 × 11 pixel Process API NDVI crop and
its contributor metadata are checksummed in ignored processed storage and
labelled `partially_cached`, not as a complete source scene.
The corridor dashboard can render that exact 5 × 11 crop as an optional,
checksum-bound NDVI layer with an enlarged inset. The control appears only for
the matching persisted prepared observation and never represents height,
current conditions, or mowing authorization.

Sprint 4 now includes local MVP identity, road-scoped manager/supervisor RBAC,
an immutable prepared review-policy version, and authenticated append-only
decisions. The dashboard keeps the bearer token in a server-only `HttpOnly`
cookie and proxies mutations through an exact-origin and CSRF-validated
boundary. It preserves accept, reject, and adjust events with actor, rationale,
idempotency, and supersession. Reviews remain incapable of creating or
authorizing field work. An accepted or adjusted inspection decision can now
create an immutable prepared inspection order with three estimated centerline
points; every database and API contract keeps execution and official reporting
blocked.

## Planned architecture

- `apps/dashboard`: Next.js management dashboard
- `apps/mobile`: offline-first Flutter Android application
- `services/api`: FastAPI application and domain use cases
- `services/geospatial-worker`: geospatial and satellite processing
- `services/ai-worker`: explainable rules and future model candidates
- `packages/contracts`: shared API and event contracts
- `infra`: Docker and database migrations
- `data`: local raw inputs, manifests, and generated products
- `docs`: architecture, decisions, and data-quality reports

## Data preparation

Place the supplied project inputs in `data/raw/`. Raw inputs are local,
immutable evidence and must not be committed. See `data/README.md` for the
expected files and handling rules.

Historical spreadsheet observations use reference date **2025-03-28**. They are
not current vegetation conditions and must not be treated as a growth series.
Simulated or prepared demonstration inputs are never eligible for training or
official reports.

## Prerequisites

- Python 3.12–3.14
- Node.js 22 or newer
- Docker Engine with Docker Compose
- PostgreSQL/PostGIS and object storage through the provided Compose stack

## Development sequence

1. Audit supplied source files and record checksums and anomalies.
2. Implement versioned, idempotent ingestion.
3. Build the PostGIS domain model and 100 m segmentation.
4. Add the cached satellite pipeline and explainable baseline.
5. Close the recommendation, approval, offline field, and reporting loop.

## API development

Python 3.12 or newer is required. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
pytest
uvicorn zenit_api.main:app --app-dir services/api/src --reload
```

Copy `.env.example` to `.env` before changing local configuration. Placeholder
passwords in `.env.example` are development defaults, never production secrets.

## Containers

With Docker and Docker Compose installed:

```bash
docker compose up --build
```

The dashboard is available at `http://localhost:3000`, the API health endpoint
at `http://localhost:8000/health`, PostGIS at port `5432`, and the MinIO console
at `http://localhost:9001`. The dashboard container waits for a healthy API and
uses the internal Compose network for server-side requests.

This workstation uses Docker Engine rootless. The project-local binaries are
ignored by Git. In a new shell, select them with:

```bash
export PATH="$PWD/.tools/docker/bin:$PATH"
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
```

PostGIS, MinIO, the API, and the dashboard have been built and validated as
healthy. Sprint 5 now includes an Android-first Flutter scaffold that supports
online login, encrypted offline download of prepared inspection orders, and
an offline demo sequence with confirmation, explicitly simulated-location
start, three prepared measurements, and finish. It deliberately has no real
GPS or field execution. It captures one photo per planned point into the
encrypted vault and synchronizes checksum-bound manifests. The API now accepts
the exact manifested bytes through a separate prepared-media upload boundary.
The app explicitly uploads accepted manifests and persists each unverified
receipt so interrupted transfers resume without repeating confirmed photos.
Uploaded objects remain encrypted, unvalidated, and non-official. The
app also downloads the prepared mowing-planning chain into the encrypted vault
for offline review. The mobile app can prepare and synchronize an explicitly
simulated mowing rehearsal with confirmation, start at an estimated prepared
point, balanced pause/resume, finish, and exactly three separate post-service
heights. The heights are encrypted for offline use, explicitly simulated and
unverified, linked to the source planned points, and collected without GPS or
photos. Candidate resources, manual readiness, and a planning decision remain
explicitly non-executable; the rehearsal has no real GPS, mowing, dispatch,
tracking, or operational approval. The app persists event/batch UUIDs, registers
its logical device, sends the exact idempotent batch, and retains local events
until a persistent accepted/rejected/conflict result arrives. The API has an
append-only, idempotent prepared-sync foundation with authenticated device
binding, persistent acknowledgements, rejected-event evidence, and conflict
preservation.
Managers can now inspect an authenticated, road-scoped read projection of each
simulated mowing rehearsal in the dashboard. The timeline revalidates event
ordering, timestamps, and every execution block, and labels a terminal event
only as `rehearsal_only_no_field_completion_claim`; it is not post-service
evidence or real mowing completion. The same projection now exposes zero to
three raw post-service heights in source-point order, with their simulated and
unverified labels. It derives no class, average, reduction, effectiveness, or
threshold result.
The sync boundary now also has a separate foundation for one simulated,
unverified post-service height per source point after the rehearsal finish.
These records do not reuse inspection measurements and explicitly keep GPS and
photos uncollected. The mobile capture screen sends a local lifecycle before
the three heights in one idempotent batch, or only the heights when that
lifecycle was already acknowledged. The API can now also persist one separate,
checksum-bound post-service photo manifest per measured point, explicitly
labelled simulated, unverified, unlocated, and not uploaded. The mobile app now
captures one later image per measured point into its encrypted vault and
synchronizes only the separate manifest. The API now has a separate verified,
AES-256-GCM encrypted upload boundary and immutable simulated receipt. After
all three manifests are accepted, the mobile app can explicitly upload their
exact bytes and persist each unverified receipt before continuing, so a partial
transfer resumes without repeating locally confirmed photos. No post-service
retrieval, review, map update, or summary exists yet.

CI repeats this validation from an empty Compose volume after the Python,
dashboard, and Flutter jobs pass. The Flutter job checks formatting, analysis,
tests, and a debug Android APK. The smoke job checks the final PostGIS schema,
API health,
an empty provenance-safe satellite response, unauthenticated write boundaries,
and dashboard/login availability without requiring raw source files or provider
credentials.

## Database migrations and ingestion

Apply migrations in numeric order before importing sources. The current local
development database must have migrations `0001` through `0031` applied. On the first
startup of a new Compose volume, Postgres applies these thirty-one up migrations in
order through `/docker-entrypoint-initdb.d`; existing volumes are never modified
by that initialization mechanism. The explicit commands below remain useful
for non-Compose environments and controlled upgrades of existing databases.

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0001_source_catalog_and_staging.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0002_allow_invalid_staging_polygons.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0003_road_axis_candidates_and_segments.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0004_satellite_analysis_foundation.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0005_satellite_scene_discovery.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0006_satellite_scene_multipolygon.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0007_partial_satellite_cache.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0008_recommendation_review_audit.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0009_identity_and_review_policy.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0010_prepared_inspection_orders.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0011_prepared_mobile_sync.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0012_prepared_demo_order_events.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0013_prepared_photo_manifest.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0014_require_demo_finish_photos.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0015_prepared_photo_upload_receipt.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0016_prepared_photo_access_audit.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0017_prepared_photo_human_review.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0018_prepared_inspection_summary.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0019_linear_prepared_photo_review_chain.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0020_serialize_prepared_photo_reviews.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0021_audited_prepared_summary_export.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0022_prepared_post_inspection_proposal.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0023_prepared_post_inspection_review.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0024_prepared_mowing_order.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0025_prepared_mowing_resource_plan.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0026_prepared_mowing_readiness_assessment.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0027_prepared_mowing_planning_approval.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0028_prepared_mowing_demo_lifecycle.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0029_prepared_mowing_post_service_measurement.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0030_prepared_mowing_post_service_photo_manifest.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zenit -d zenit \
  < infra/migrations/0031_prepared_mowing_post_service_photo_upload_receipt.sql
```

Migration `0008` starts the Sprint 4 management foundation with immutable,
idempotent recommendation-review events. It records accept/reject/adjust
decisions, actor subject, rationale, source channel, and supersession without
creating or authorizing field work. See
`docs/decisions/ADR-0007-append-only-recommendation-reviews.md`.

Migration `0009` adds local MVP users, prepared manager/supervisor roles scoped
to a road, and immutable review-policy versions. The initial policy is a
configurable project placeholder rather than an official Motiva value, and a
database constraint fixes `authorizes_field_work=false`. See
`docs/decisions/ADR-0008-local-mvp-identity-and-review-policy.md`.

Migration `0010` adds an immutable prepared inspection-order policy, orders,
and exactly three centerline-fraction points. An order requires the effective
versioned review, an authenticated non-simulated road role, and a rationale.
Constraints fix field execution and official reporting to false. The policy and
point fractions are prepared placeholders, not official Motiva values. See
`docs/decisions/ADR-0010-prepared-inspection-order-foundation.md`.

Migration `0011` adds immutable prepared device registrations, revocations,
sync batches/events/conflicts, and prepared field measurements. Duplicate
batches and events are replay-safe; conflicting event payloads preserve both
versions. Every synchronized measurement remains non-operational and
ineligible for official reporting. See
`docs/decisions/ADR-0012-prepared-mobile-sync-foundation.md`.

Migration `0012` adds append-only simulated lifecycle events for the prepared
demo flow. Confirmation, simulated-location start, and finish must occur once
in order; finish requires measurements at all three planned points. These
events do not mutate or authorize the prepared order. See
`docs/decisions/ADR-0014-simulated-prepared-order-lifecycle.md`.

Migration `0013` adds immutable prepared photo manifests linked to a planned
point, actor, device, timestamp, checksum, size, and media type. A manifest is
always `not_uploaded`, `not_validated`, and non-official; it is not evidence
that object content exists. See
`docs/decisions/ADR-0016-prepared-photo-manifest-foundation.md`.

Migration `0014` requires three distinct prepared point-photo manifests before
a new simulated demo finish can be persisted. It does not claim that their
content was uploaded or validated.

Migration `0015` adds an immutable upload receipt bound to the exact manifest,
actor, device, checksum, object version, and ETag. The API encrypts photo bytes
with AES-256-GCM before writing them to the private, versioned media bucket.
Receipts remain `uploaded_unverified`, ruler-unvalidated, prepared, and
ineligible for official reporting. See
`docs/decisions/ADR-0018-verified-encrypted-prepared-media-upload.md`.

Migration `0016` adds append-only access events for successful human-review
retrievals. PostgreSQL repeats active user, road-role, exact receipt, and safety
status checks before recording delivery. See
`docs/decisions/ADR-0020-authorized-prepared-media-retrieval.md`.

Migration `0017` adds a versioned prepared photo-review policy and append-only,
idempotent human decisions for image quality and ruler visibility. Even an
accepted review remains prepared and ineligible for field evidence, model
training, official reporting, or field authorization. See
`docs/decisions/ADR-0021-prepared-photo-human-review.md`.

Migration `0018` adds a versioned, immutable prepared inspection summary. It
requires a finished simulated lifecycle, exactly three measurements, and three
effectively accepted photo reviews, then preserves historical N1/N2/N3 counts.
Every summary remains simulated-location, prepared, non-operational, excluded
from training and official reports. See
`docs/decisions/ADR-0022-prepared-inspection-summary.md`.

Migration `0019` makes each prepared photo's review history a single linear
chain. After the first review, every correction must supersede the effective
leaf, preventing parallel outcomes from satisfying summary evidence gates.
Migration `0020` serializes concurrent review inserts per photo before checking
that chain, closing the race between simultaneous first reviews or corrections.

Migration `0021` adds immutable, idempotent CSV-export audit events for prepared
inspection summaries. PostgreSQL repeats current manager/supervisor road access
and every simulated, prepared, non-official, non-authorizing safety gate. Each
event records purpose, export schema version, byte size, and SHA-256 checksum.
See `docs/decisions/ADR-0023-audited-prepared-summary-csv-export.md`.

Migration `0022` adds the versioned, immutable prepared post-inspection
proposal. PostgreSQL applies 10 cm to special zones and 30 cm elsewhere, then
returns only `monitor` or `mowing_review`. Every result explicitly requires a
separate human review and cannot create or authorize mowing work. See
`docs/decisions/ADR-0024-prepared-post-inspection-proposal.md`.

Migration `0023` adds append-only human decisions for prepared post-inspection
proposals. Corrections form one serialized linear supersession chain; rejection
and adjustment require rationale, and every outcome remains prepared,
non-official, and unable to authorize mowing. See
`docs/decisions/ADR-0025-prepared-post-inspection-human-review.md`.

Migration `0024` adds an immutable prepared mowing-order foundation. Only the
effective human review selecting `mowing_review` can create one. Team and
equipment remain unassigned, weather and safety remain pending, and the order
cannot authorize field execution. See
`docs/decisions/ADR-0026-prepared-mowing-order-foundation.md`.

Migration `0025` adds append-only candidate resource plans for prepared mowing
orders. Team and equipment references remain unverified placeholders pending
external validation; assignment stays `unassigned` and field execution remains
blocked. See `docs/decisions/ADR-0027-prepared-mowing-resource-plan.md`.

Migration `0026` adds append-only manual weather and safety assessments tied to
the effective candidate resource plan. Declared sources are mandatory and all
results remain prepared, pending validation, and non-authorizing. See
`docs/decisions/ADR-0028-prepared-mowing-readiness-assessment.md`.

Migration `0027` adds a segregated planning-decision chain. A positive decision
requires prepared `clear` weather and safety results but never satisfies
operational approval or authorizes execution. Dual-approval rules remain
pending official policy validation. See
`docs/decisions/ADR-0029-prepared-mowing-planning-approval.md`.

Migration `0028` adds append-only events for a strictly simulated mowing
rehearsal: confirmation, start with an explicitly simulated coordinate,
balanced pause/resume, and finish. The effective prepared planning decision is
required, but operational approval and every execution/reporting/training flag
remain false. See
`docs/decisions/ADR-0031-prepared-mowing-demo-lifecycle.md`.

Migration `0029` adds one immutable simulated post-service height per source
point after the rehearsal finish. The new sync event remains unverified,
collects neither GPS nor photo, and cannot authorize work, training, or official
reporting. See
`docs/decisions/ADR-0035-simulated-mowing-post-service-measurement-foundation.md`.

Migration `0030` adds one separate checksum-bound post-service photo manifest
per mowing-order/source-point pair after its simulated measurement. It records
only `not_uploaded`, unvalidated, no-location metadata and cannot claim server
possession, image quality, field execution, training eligibility, or official
reporting. See
`docs/decisions/ADR-0038-simulated-mowing-post-service-photo-manifest-foundation.md`.

Migration `0031` adds an immutable verified-possession receipt for the exact
post-service bytes. The API encrypts them with AES-256-GCM before a separate
versioned object namespace, while every simulated, unverified, non-operational,
non-training, and non-official label remains fixed. See
`docs/decisions/ADR-0040-verified-encrypted-simulated-mowing-photo-upload.md`.

The mobile client can cache this prepared mowing-planning chain for offline,
guarded demonstration. It validates provenance links and every execution block
before accepting a snapshot; planning approval never becomes operational
approval. Eligible snapshots can drive only the encrypted simulated rehearsal
described in ADR-0031, followed by three separate simulated and unverified
post-service heights with persistent UUIDs and idempotent sync. See
`docs/decisions/ADR-0030-read-only-prepared-mowing-mobile.md` and
`docs/decisions/ADR-0032-mobile-prepared-mowing-demo-orchestration.md`, plus
`docs/decisions/ADR-0036-mobile-simulated-mowing-post-service-measurements.md`.

The authenticated management projection for synchronized rehearsals is
available at:

```text
GET /v1/prepared-mowing-rehearsals?limit=50
```

It returns only actor-accessible, non-operational prepared orders and derives
the rehearsal state and timeline from immutable events. It excludes actor,
device, and coordinate details. The response includes raw simulated,
unverified post-service heights when present, but never claims verified
vegetation evidence, field execution, mowing effectiveness, or official
completion. See
`docs/decisions/ADR-0034-read-only-prepared-mowing-rehearsal-history.md` and
`docs/decisions/ADR-0037-read-only-simulated-mowing-post-service-history.md`.

The public, read-only management queue is available at:

```text
GET /v1/recommendations?limit=50
```

It returns analysis, segment/zone, road code, explanation, versions, review
count, and an awaiting/recorded review state without reviewer identity. Every
item explicitly reports `authorizes_field_work=false`. Recorded items include
their policy version/status without exposing reviewer identity. The dashboard
exposes the same queue at `/recommendations`; unauthenticated visitors retain a
read-only view, while authenticated users only receive decision controls for
roads where they hold a manager or supervisor role.
Pre-migration review rows, if present in another environment, remain explicitly
`review_recorded_policy_pending` rather than being assigned a policy
retroactively.
Each queue item links to a shareable corridor URL such as `/?segment=195`,
opening the geometric segment and its satellite evidence directly without
presenting the index as official stationing.

Create a local reviewer interactively after migration `0009`; no default user
or password is committed:

```bash
zenit-user \
  --email manager@example.test \
  --display-name "Local MVP Manager" \
  --road-code SP021 \
  --role manager
```

Obtain a 30-minute bearer token using the email in OAuth2's `username` field:

```text
POST /v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=manager%40example.test&password=<local-password>
```

The authenticated user's own identity and road-scoped roles are available at
`GET /v1/auth/me`. The dashboard login at `/login` uses this contract
server-side: the bearer token is never returned to browser JavaScript or stored
in local storage. Mutating dashboard requests require a separate CSRF token,
an exact matching `Origin`, and `SameSite=Strict` cookies. Set
`DASHBOARD_PUBLIC_ORIGIN` to the externally visible origin and require HTTPS
with `DASHBOARD_COOKIE_SECURE=true` in staging and production.

Record an append-only decision with an authenticated actor and a replay-safe
key:

```text
POST /v1/recommendations/{vegetation_analysis_id}/decisions
Authorization: Bearer <access-token>
Idempotency-Key: <unique-client-operation-key>
Content-Type: application/json

{"decision":"rejected","rationale":"Field inspection required"}
```

Rejected and adjusted decisions require a rationale; adjusted decisions also
require `adjusted_recommendation`. A successful response always reports
`authorizes_field_work=false` and whether the prepared policy calls for dual
review.

After an accepted or adjusted review whose effective action is `inspect`, an
authenticated reviewer can prepare a non-operational inspection order:

```text
POST /v1/work-orders
Authorization: Bearer <access-token>
Idempotency-Key: <unique-client-operation-key>
Content-Type: application/json

{
  "source_review_id": "<effective-review-uuid>",
  "planning_rationale": "Low-confidence evidence requires field inspection"
}
```

`GET /v1/work-orders?limit=50` lists only orders on roads assigned to the
authenticated user. Responses include the source data-status labels and three
EPSG:4326 planning points, while explicitly reporting
`authorizes_field_work=false`, `eligible_for_field_execution=false`, and
`eligible_for_official_reporting=false`. The points are derived from the
estimated segment centerline and are not surveyed field locations.

Local MVP authentication still has no corporate identity, refresh-token,
password-reset, or login-rate-limiting flow. It must not be exposed directly to
the internet; these controls are a bounded development/MVP security boundary.

Register a client-generated Android device identifier with the authenticated
user before synchronization:

```text
POST /v1/mobile/devices
Authorization: Bearer <access-token>
Content-Type: application/json

{"device_id":"<device-uuid>","platform":"android","app_version":"1.0.0+1"}
```

`POST /v1/sync/batch` accepts idempotent prepared event batches. It persists
prepared `measurement/create` events and the demo-only `work_order/confirm`,
`work_order/start`, and `work_order/finish` sequence. Demo lifecycle events are
explicitly `simulated`; start requires a simulated coordinate and finish
requires three persisted point measurements. They never change the immutable
prepared order or authorize field activity or official reporting. Responses
contain `accepted`, `rejected`, `conflicts`, and `next_sync_cursor`.
`photo/prepare` registers checksum-bound metadata only and explicitly reports
that the content has not been uploaded or validated.

After a separate mowing rehearsal reaches `finish`, the same endpoint accepts
one `mowing_measurement/create` event per source planned point. The payload is
fixed to simulated, unverified post-service input without GPS or photo, and is
ineligible for field execution, model training, or official reporting. It does
not claim real mowing completion or update inspection evidence.

After its manifest is accepted, upload the exact prepared JPEG or PNG bytes:

```text
POST /v1/media/{photo_id}
Authorization: Bearer <access-token>
X-Zenit-Device-ID: <registered-device-uuid>
Content-Type: multipart/form-data; boundary=...
```

The endpoint verifies the signature, size, checksum, active actor/device and
current road role. It stores application-encrypted bytes and an immutable
version receipt, but deliberately returns only prepared/unverified/non-official
status. Automated ruler validation, decoded-image safety, and retention policy
remain future work. The mobile client uploads only after the corresponding
manifest has a persistent accepted result, persists each
`uploaded_unverified` receipt before continuing, and skips already received
photos when a partial upload is retried. Upload remains an explicit user action
and never changes the prepared/non-official boundary.

An authenticated manager or supervisor with a current non-simulated role on
the photo's road may retrieve the exact decrypted bytes for human review:

```text
GET /v1/media/{photo_id}
Authorization: Bearer <access-token>
```

The API reads the immutable object version, verifies AES-GCM authentication,
byte size, and SHA-256 before returning it with `no-store`, `nosniff`, and
explicit prepared/unverified/non-official headers. Unauthorized and absent
photos share the same not-found boundary. Retrieval does not validate image
quality, ruler presence, location, or vegetation height.

Record a human review with a unique retry key:

```text
POST /v1/media/{photo_id}/reviews
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"decision":"accepted","quality_status":"accepted","ruler_status":"visible"}
```

Rejected and inconclusive outcomes require a rationale. Acceptance only records
that a reviewer could assess the prepared image and see a ruler; it does not
validate a height measurement or make the photo operational or official.

Authenticated reviewers discover only photos on roads covered by their current
non-simulated manager/supervisor roles:

```text
GET /v1/photo-review-queue?limit=50
Authorization: Bearer <access-token>
```

The queue exposes order, segment, zone, planned-point sequence, capture/upload
timestamps, media metadata, and the latest effective review. It omits reviewer
identity, device identifiers, object-store coordinates, and encryption details.
The authenticated dashboard exposes this workflow at `/photo-reviews`. Its
server-side proxies keep the bearer token in the `httpOnly` session cookie,
enforce origin and CSRF checks on writes, accept only JPEG/PNG responses, and
preserve `no-store`, `nosniff`, prepared, and non-official response boundaries.

Generate the immutable prepared return summary after all evidence gates pass:

```text
POST /v1/work-orders/{work_order_id}/prepared-summary
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"generation_rationale":"Consolidate the prepared demo return"}
```

The response reports minimum, maximum, mean, and N1/N2/N3 counts. These are
aggregates of prepared typed measurements, not values inferred from photos and
not an official operational report.

Current non-simulated managers and supervisors can list only summaries from
their assigned roads:

```text
GET /v1/prepared-inspection-summaries?limit=50
Authorization: Bearer <access-token>
```

At `/photo-reviews`, the authenticated dashboard groups the three planned points
by order. Once every latest effective review is accepted with accepted quality
and a visible ruler, it offers a CSRF-checked summary-generation form. Generated
minimum, mean, maximum, and N1/N2/N3 counts remain visibly labeled as prepared,
simulated, non-operational, and ineligible for official reporting.

Generated summaries can be exported as an audited prepared CSV:

```text
POST /v1/prepared-inspection-summaries/{summary_id}/exports
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"export_purpose":"Share the prepared result for review"}
```

The deterministic artifact is versioned, checksum-addressed, formula-safe for
user-authored cells, limited to one megabyte, and prominently states that it is
a simulated prepared demo export—not an official report or field authorization.
The dashboard verifies these labels and checksum before delivering the download.

Create the prepared post-inspection planning signal from a generated summary:

```text
POST /v1/prepared-inspection-summaries/{summary_id}/post-inspection-proposal
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"creation_rationale":"Apply the prepared threshold rule to the reviewed return"}
```

The authenticated proposal list is available at
`GET /v1/prepared-post-inspection-proposals?limit=50`. A threshold breach yields
`mowing_review`, never a mowing authorization. The `/photo-reviews` dashboard
shows the comparison and keeps the human-decision state visibly pending.

Record or correct the human planning decision:

```text
POST /v1/prepared-post-inspection-proposals/{proposal_id}/decisions
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"decision":"adjusted","adjusted_recommendation":"monitor","rationale":"Keep monitoring in the prepared scenario"}
```

The effective review is returned in the authenticated proposal list. Accepting
`mowing_review` records agreement with a prepared planning signal only; it does
not create a mowing order or authorize field activity.

Prepare or list non-executable mowing orders:

```text
POST /v1/prepared-mowing-orders
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"source_review_id":"<effective-review-uuid>","planning_rationale":"Prepare planning without authorizing execution"}

GET /v1/prepared-mowing-orders?limit=50
Authorization: Bearer <access-token>
```

The creation endpoint rejects rejected, superseded, or effective `monitor`
reviews. Its result remains prepared, simulated-location, non-official, and
ineligible for field execution.

Record or correct candidate resource references:

```text
POST /v1/prepared-mowing-orders/{mowing_order_id}/resource-plans
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"team_reference":"candidate label pending validation","equipment_reference":"candidate label pending validation","planning_rationale":"Prepare resource planning without assignment"}
```

The API and dashboard identify these values as prepared placeholders. They do
not confirm availability, create assignments, or change any execution gate.

Record or correct the manual readiness assessment:

```text
POST /v1/prepared-mowing-orders/{mowing_order_id}/readiness-assessments
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"resource_plan_id":"<effective-plan-uuid>","weather_result":"inconclusive","weather_source_reference":"manual source pending validation","safety_result":"inconclusive","safety_source_reference":"manual checklist pending validation","assessment_rationale":"Record prepared context without clearance"}
```

Even two `clear` results are manual prepared statements only. They do not
authorize work, schedule a crew, or make the order field-executable.

Record or correct the segregated planning decision:

```text
POST /v1/prepared-mowing-orders/{mowing_order_id}/planning-approvals
Authorization: Bearer <access-token>
Idempotency-Key: <client-generated-stable-key>
Content-Type: application/json

{"readiness_assessment_id":"<effective-assessment-uuid>","decision":"approved_for_planning","decision_rationale":"Approve only the prepared planning scenario"}
```

`approved_for_planning` is not an operational approval. The response fixes
`operational_approval_satisfied=false`, `authorizes_field_work=false`, and
`eligible_for_field_execution=false`.

Use `zenit-import` for one immutable raw file at a time. Full examples are in
`docs/architecture/source-ingestion.md`.

For the prepared Sprint 3 validation AOI, the idempotent Sentinel flow is:

```bash
zenit-satellite \
  --segment-index 195 \
  --zone left \
  --from-date 2026-07-01 \
  --to-date 2026-08-07
```

It is deliberately restricted to prepared, non-operational geometry. See
`docs/architecture/satellite-discovery.md` before changing the AOI or period.

## Segment GeoJSON API

The current estimated axis is queryable by bounding box:

```text
GET /v1/roads/SP021/segments?min_lon=-46.84&min_lat=-23.64&max_lon=-46.72&max_lat=-23.40
```

The response is GeoJSON in EPSG:4326. Segment properties explicitly report
`estimated`, `needs_validation`, and `eligible_for_operations=false`; see
`docs/data-quality/km-axis-quality.md` before using this dataset.

## Analysis preview API

The Sprint 3 baseline can be evaluated without persisting a result:

```text
POST /v1/analysis/preview
```

The request labels scene quality and status, reflectance inputs, valid-pixel
coverage, zone type, and—when available—an independently observed height with
its provenance status. NDVI alone never becomes a height estimate. Low-quality
or non-real data returns `inconclusive` and `inspect`; a real height over the
applicable 30 cm or 10 cm threshold returns `mowing_review`, which still requires
human approval. See `docs/decisions/ADR-0005-quality-gated-satellite-baseline.md`.

### Local cached NDVI preview

The checksummed 5 × 11 Sentinel-2 NDVI crop can be inspected in the
self-contained [cached NDVI preview](docs/previews/sentinel-ndvi-preview.html).
When the ignored checksummed cache is available, regenerate it without network
access or third-party Python packages:

```bash
python scripts/render_cached_ndvi_preview.py
```

The renderer verifies the source GeoTIFF and provider-metadata checksums before
writing the preview and its lineage manifest. The page clearly labels the AOI
as prepared, estimated, non-operational, and ineligible for official reporting.
No true-color RGB raster is currently cached.

## Satellite observation API

Persisted satellite evidence for a 100 m segment is available read-only:

```text
GET /v1/segments/{segment_id}/satellite-observations?limit=50
```

The response preserves scene and zone data-status labels, quality metrics,
explanations, rule/processor versions, approval requirements, and artifact
checksums. It intentionally omits internal storage locations and provider
credentials. Satellite quality and NDVI are not presented as vegetation height
or authorization for mowing; prepared or low-confidence evidence remains
inconclusive, requires inspection, and is ineligible for official reporting.

## Dashboard development

The dashboard renders the candidate SP-021 axis as selectable 100 m segments
and keeps the data-quality and operational-use warnings visible. Selecting a
segment loads its latest persisted satellite observation through a server-side
proxy, including acquisition date, NDVI, valid-pixel coverage, confidence,
recommendation, reporting gate, rule version, and artifact checksum. It does
not substitute simulated data or presume a result when either API is
unavailable. When multiple observations exist, the audit history keeps each
run selectable with its own acquisition, zone, versions, gates, and artifact
checksums instead of overwriting earlier evidence. The segment-index locator
provides direct keyboard-accessible navigation—for example, index `195` selects
the prepared validation AOI without presenting that geometric index as an
official kilometer marker.

At `/recommendations`, the public queue remains read-only. After a local user
signs in at `/login`, the server resolves their current road-scoped roles and
renders append-only accept, reject, and adjust controls only for matching
roads. Corrections supersede the latest review instead of modifying history.
The API repeats every authorization check and derives the actor solely from the
verified bearer token. For an effective inspection decision, the dashboard can
also prepare the three non-operational points through the same session/CSRF
boundary. None of these controls authorizes field work.

History responses report the returned count, total count, applied limit, and an
explicit `truncated` flag. The dashboard warns when it is showing only the most
recent subset, so a bounded response cannot be mistaken for the complete audit
history.

Install the declared workspace dependencies and start the API before running the
dashboard:

```bash
npm install
npm run dev --workspace @zenit/dashboard
```

The server-side dashboard request uses `INTERNAL_API_URL` and defaults to
`http://localhost:8000`. Validate it from the repository root with:

```bash
npm run dashboard:lint
npm run dashboard:typecheck
npm run dashboard:test
npm run dashboard:build
```

The Android-first mobile scaffold uses the locked Flutter dependencies under
`apps/mobile`. From that directory, validate the current offline demo slice
with:

```bash
../../.tools/flutter/bin/flutter --no-version-check --suppress-analytics pub get --enforce-lockfile
../../.tools/flutter/bin/dart format --output=none --set-exit-if-changed lib test
../../.tools/flutter/bin/flutter --no-version-check --suppress-analytics analyze
../../.tools/flutter/bin/flutter --no-version-check --suppress-analytics test
```

The emulator-only default API URL is `http://10.0.2.2:8000`. Production builds
must pass an HTTPS URL through `--dart-define=ZENIT_API_BASE_URL=...`; cleartext
traffic is enabled only by the debug Android manifest.
