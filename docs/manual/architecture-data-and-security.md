# Architecture, data and security

This chapter maintains and updates chapters 9-13 of the original master manual.
Accepted ADRs and versioned contracts remain the authoritative record for individual
technical decisions.

## Implemented architecture

ZENIT is a modular monorepo. It deliberately keeps deployment simple while separating
domain boundaries in code.

```text
Next.js dashboard ---- server-held session ---- FastAPI API
        |                                      /         \
        |                                PostgreSQL     private MinIO
        |                                  + PostGIS     object storage
        |
Flutter Android ---- bearer session + encrypted local vault

Python geospatial worker ---- external catalog/process providers
```

Primary directories:

```text
apps/dashboard/                 Next.js and TypeScript dashboard
apps/mobile/                    Flutter Android client and offline workflow
services/api/                   FastAPI domain/API implementation
services/geospatial-worker/     provider-neutral discovery and processing code
packages/                       shared package space
infra/migrations/               append-only PostgreSQL/PostGIS migrations
contracts/openapi.json          versioned public API contract
scripts/                        reproducible validation and support commands
docs/                           living specification, ADRs and evidence
data/raw/                       immutable, ignored local sources
data/processed/                 derived local outputs with lineage
```

There is no production microservice topology, message broker, Kubernetes platform,
corporate identity provider, or generic raster tile service. Those are future choices,
not hidden parts of the current system.

## Runtime components

### Dashboard

The dashboard uses Next.js with server-side session handling. Authentication tokens
remain in HttpOnly cookies and server routes proxy protected API operations. Exact
origin and CSRF controls protect state-changing requests. Shared navigation and
progressive disclosure are established, while the broader visual redesign remains
incremental.

The map uses MapLibre and a configurable raster base. Road segments and vegetation
features come from the ZENIT API. A list alternative, attribution, source date, and
data-status labels are required. Planet or other private provider credentials must
never appear in browser URLs.

### API

The FastAPI service owns authentication, road-scoped authorization, validation,
workflow transitions, audit events, and protected object access. PostgreSQL queries
recheck actor and target state; hiding a dashboard action is never an authorization
control.

The OpenAPI document is generated from the application and committed as
[`contracts/openapi.json`](../../contracts/openapi.json). Contract changes require
implementation, generated schema, tests, and consumer migration in one reviewed
delivery.

### Mobile

The Flutter client supports prepared inspection and mowing-demo workflows. Tokens,
cached orders, drafts, manifests, bytes, and sync outcomes use encrypted local storage
where designed. Stable identifiers make retries idempotent. The app validates
fail-closed JSON schemas and never supplies actor identity or promotes eligibility
flags.

The current Android release evidence covers a demonstrative debug APK. Production
signing, device enrollment, remote revocation, distribution, and support remain
blocked.

### Geospatial worker

The Python worker isolates provider-specific authentication, payloads, pagination,
and metadata behind normalized acquisition objects. Current capabilities include
Sentinel Hub, INPE BDC/CBERS, and discovery-only Planet adapters. External response
bodies and credentials are not logged.

Network access, dependency installation, scene orders, and downloads require an
explicit scoped task. Provider discovery does not make a scene quality-approved,
cached, analyzed, current, or operational.

## Data layers

| Layer | Meaning | Mutability |
| --- | --- | --- |
| raw | bytes exactly as received, plus checksum | immutable |
| staging | extracted structures and anomalies | reproducible/disposable |
| normalized | validated geometry and attributes with inference status | versioned |
| processed | indices, crops, masks, aggregates, and quality outputs | reproducible and checksummed |
| model output | prediction, confidence, version, and explanation | immutable per run |
| observed | human field photos, GPS, measurements, and reviews | append-only where evidentiary |
| operational | recommendations, approvals, plans, work, and incidents | stateful and audited |

The current repository uses raw, normalized, processed, observed, and operational
concepts, but many observed/operational-looking examples are deliberately prepared or
simulated. Layer name never overrides `data_status` or eligibility.

## Core data model

The implemented migrations establish these principal groups:

- source files, import runs, road-axis candidates, road segments, and segment zones;
- satellite scenes, cached artifacts, analysis runs, vegetation analyses, and rule
  versions;
- users, road roles, authentication sessions, and login-throttle state;
- recommendation reviews and prepared inspection orders with planned points;
- encrypted photo manifests, upload receipts, access events, and human reviews;
- prepared inspection summaries, proposals, and append-only proposal reviews;
- prepared mowing orders, resource plans, readiness assessments, and planning
  approvals;
- simulated rehearsal events, post-service measurements/photos/reviews, summaries,
  exceptions, and exception reviews.

Migrations are append-only and currently span `0001` through `0042`. Existing Docker
volumes are not automatically migrated merely because a newer SQL file exists; apply
only missing migrations using the documented controlled procedure.

## Database invariants

- geometry columns use explicit SRIDs and suitable geometry types;
- source identity and import lineage are stable and checksummed;
- prepared/simulated false eligibility values are reinforced by constraints;
- actor IDs for human actions come from authenticated server context;
- superseding review records preserve the prior decision rather than overwriting it;
- idempotency keys prevent silent duplicate workflow events; and
- a discovered satellite scene is distinct from a cached or processed raster.

API-001 found contract-preserving query improvements still available. Inspection
orders can execute `1 + 2N` queries, prepared mowing orders `1 + N`, and rehearsal
history `1 + 3N`. Queue contracts also expose bounded results without recoverable
cursor pagination. See the [queue analysis](../api/view-model-pagination-analysis.md).

## API principles

Public endpoints follow these rules:

- stable `/v1` paths and generated OpenAPI;
- strict request/response models with unexpected fields rejected;
- server-derived identity and road-scoped authorization;
- bounded collection limits;
- explicit timestamps, identifiers, status, provenance, and warnings;
- correlation IDs and a stable error envelope;
- idempotency for retryable writes;
- no object-storage URI, provider credential, stack trace, or secret in a response;
- no client-controlled operational, training, or reporting eligibility; and
- human decisions remain distinguishable from model/rule outputs.

The exact endpoint inventory belongs in OpenAPI. This manual intentionally avoids a
second hand-maintained endpoint list that can drift.

## Mobile synchronization

A synchronization batch retains user, device, event, and source identifiers. The
server validates authentication, road role, target state, policy, idempotency, and
payload shape. Per-item outcomes distinguish accepted, rejected, and conflict states.

Media synchronization is manifest-first:

```text
encrypted local draft
  -> metadata manifest with stable photo ID and SHA-256
  -> server authorization and manifest registration
  -> bounded byte upload
  -> media type, length and checksum verification
  -> application encryption and private versioned object storage
  -> immutable receipt and later human review
```

Retries reuse identifiers; a retry must not create a second event or silently replace
evidence.

## Satellite provider boundary

### Sentinel and CBERS

Sentinel Hub uses backend-only OAuth client credentials and bounded token reuse. INPE
BDC uses a STAC catalog boundary with an optional backend token. The products differ
in resolution, processing level, spectral meaning, quality metadata, and cadence and
must not be merged as interchangeable values.

The historical technical PDF is summarized in the
[Sentinel/CBERS companion](../reference/sentinel-cbers-api-guide.md). Current behavior
is documented in [`docs/architecture/satellite-discovery.md`](../architecture/satellite-discovery.md).

### Planet

Planet support is restricted to `PSScene` metadata discovery through the backend
Data API boundary. The API key is a secret, sent only in an authorization header.
The current CLI does not order, download, persist, tile, or analyze Planet imagery.

Future work must be split into account/catalog validation, persistence with an
approved migration, quota accounting, Orders/downloads, checksums and lineage,
controlled tile proxy/cache, and a small offline pilot. Catalog discovery alone does
not consume authorization for later stages.

## Security model

The [incremental threat model](../security/incremental-threat-model.md) defines assets,
actors, trust boundaries, threats, controls, and residual risk. Its central invariants
are part of this manual.

### Authentication and sessions

The P0 uses local identities with Argon2 password hashes, short-lived signed access
tokens, persisted session registration, individual logout revocation, and persistent
login throttling. Dashboard cookies are HttpOnly and SameSite strict. Protected API
requests recheck that the session and user remain active.

This is not an internet-facing identity system. Corporate IdP, MFA, recovery,
administrative revocation, recertification, service accounts, and production edge
controls remain unresolved.

### Authorization and audit

Manager and supervisor actions are constrained by road-role assignment and versioned
policy. The API and database validate the actor and source object. Reviews and access
events preserve actor, time, policy, rationale, and supersession.

Every new endpoint needs negative authentication and cross-road authorization tests.
UI role visibility is a convenience only.

### Media and privacy

The current media boundary verifies JPEG/PNG declarations, size, SHA-256, manifest,
actor, role, device, and target before encrypted storage. Retrieval verifies exact
version, decryption, checksum, and length and records access.

These controls do not provide safe decoder isolation, malware scanning, EXIF
anonymization, face/plate handling, retention, legal hold, key recovery, or production
IAM. Real field media and an operational pilot remain blocked until those policies
and controls exist.

### Availability and dependency failure

Health and readiness are distinct. Required PostgreSQL and object-storage failures
make readiness fail closed. Compose startup uses dependency-aware health checks, and
the fresh-stack verifier checks public, protected, and rendered-dashboard boundaries.

Production SLOs, alerting, redundancy, backup, restoration, and incident ownership are
not implemented.

### Browser security

The dashboard sets anti-framing, content-type, referrer, and permissions protections
and a partial CSP. Exact public origin, secure cookies, TLS termination, HSTS, and a
nonce/hash script policy must be validated at an approved edge before exposure.

## Secrets and configuration

Secrets stay in local environment configuration or a future approved secret manager.
Never commit or print `.env`, resolved Compose configuration, JWT keys, media keys,
database URLs with passwords, provider keys, or temporary tokens.

Important backend-only values include authentication signing material, fixed demo
session secret, object-storage credentials and media encryption key, Copernicus OAuth
credentials, optional BDC token, and Planet API key. No provider or storage credential
may use a `NEXT_PUBLIC_*` variable or be embedded in a browser/mobile URL.

Use [`docs/team/external-services-and-secrets.md`](../team/external-services-and-secrets.md)
for current variable names and environment rules.

## Engineering standards

- English for code, identifiers, technical filenames, branches, and commits;
- type checks, lint, tests, generated-contract verification, and builds proportional
  to the change;
- `feature/`, `fix/`, or `docs/` branch with one cohesive ticket;
- no direct push to `main`, force push, history rewrite, or destructive data command;
- no production dependency, architecture, migration, or network expansion without
  explicit approval;
- no modifications under `data/raw/`;
- no source documents, secrets, large imagery, or personal data in Git; and
- every completed repository change is committed, pushed, and handed off through a
  reviewed pull request.
