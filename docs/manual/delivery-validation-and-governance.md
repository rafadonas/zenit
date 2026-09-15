# Delivery, validation and governance

This chapter replaces the now-historical sprint plan in chapters 14-21 of the
original master manual with the repository's current delivery model.

## Maturity levels

### P0 - reliable academic demonstration

P0 demonstrates a coherent, testable chain using clearly labeled real provider
metadata, estimated geometry, prepared workflow records, and simulated field/mowing
events. It requires reproducibility, safety gates, accessibility, and honest limits.
It does not require or imply production operation.

### P1 - controlled pilot

P1 requires authoritative geometry and source data, approved identity, privacy,
retention, device, media, staging, observability, backup, restoration, and incident
policies. Real field work and model/data use must be formally scoped.

### P2 - advanced intelligence and scale

P2 can introduce reviewed models, shadow mode, drift monitoring, optimized workflows,
and broader corridors only after validated datasets, P1 controls, and explicit human
promotion gates exist.

No calendar date or demonstration success promotes a capability between levels.

## Current implementation status

The repository currently provides:

- a migrated local PostgreSQL/PostGIS database and private MinIO boundary;
- imported/normalized road evidence with checksum and quality documentation;
- 100 m segments and separate zone geometries derived from an estimated axis;
- provider-neutral satellite discovery and a small prepared Sentinel validation;
- explainable recommendation and append-only human review;
- prepared inspection orders, mobile drafts/sync, verified media, review, summary,
  proposal, and export;
- prepared mowing planning plus simulated rehearsal, evidence, review, summary,
  exception, and export;
- local authentication, road roles, CSRF/origin controls, session revocation, and
  login throttling;
- a responsive dashboard baseline, vegetation map, and mobile debug build evidence;
  and
- automated API, OpenAPI, dashboard, mobile, and fresh-Compose gates.

It does not provide:

- official road axis or homologated source attributes;
- operational identity or internet-facing deployment;
- real dispatch, GPS tracking, mowing execution, or official report;
- approved field-media privacy and retention controls;
- a production backup/restore, observability, or incident program;
- a validated tree/grass/shrub model or training dataset;
- a complete current satellite scene covering the corridor; or
- authority to act on behalf of Motiva, a regulator, concessionaire, or field team.
  ZENIT branding is academic and project-owned under ADR-0069.

See [`docs/team/current-state-and-gaps.md`](../team/current-state-and-gaps.md) for
the detailed living inventory.

## Team delivery model

The work is routed across four tracks:

| Person | Primary responsibility | Cross-review responsibility |
| --- | --- | --- |
| Rafael | integration, API, authentication, authorization, security, CI/Compose | contracts and security impact |
| Guilherme | design system, dashboard, accessibility, responsive map experience | web/mobile UX and visual semantics |
| Lucas | geospatial processing, providers, data quality, Planet, vegetation intelligence | geospatial and scientific claims |
| Gabriel | Flutter architecture, offline field workflow, encrypted drafts and sync | mobile contract and field impact |

Shared files such as OpenAPI, migrations, Compose, CI, global styles, lockfiles, and
central mobile controllers require reservation and coordination. Assignment is a
conflict-management mechanism, not exclusive ownership of knowledge.

The authoritative queue and dependencies are in
[`docs/team/work-packages.md`](../team/work-packages.md). Each contributor continues
the first eligible package in their queue, one ticket and pull request at a time.

## Current completed integration baseline

As of 2026-09-13, Rafael's first three integration packages are merged:

- QA-001: reproducible E2E journey matrix and automated baseline;
- SEC-001: incremental threat model and negative-test traceability; and
- API-001: measured queue payload/call/query analysis.

This record describes the assessed revision date, not a permanent ticket dashboard.
Confirm branch and PR state before starting new work.

## Testing strategy

### Automated gates

| Area | Minimum evidence |
| --- | --- |
| Python/API/geospatial | Ruff, Pytest, generated OpenAPI check, SRID/idempotency/security tests |
| Dashboard | lint, TypeScript check, Vitest, production build, route/security tests |
| Mobile | Dart format check, Flutter analyze, Flutter tests, affected build evidence |
| Database | ordered migration validation, constraints, and forward/down check when applicable |
| Fresh stack | dependency-aware Compose health and public/protected/rendered smoke boundaries |

Run the smallest relevant gate during development and the complete affected gates
before delivery. Passing unit tests does not prove browser, device, provider, or
operational behavior.

### E2E baseline

The [QA-001 matrix](../qa/e2e-journey-matrix.md) defines ten reproducible scenarios:

1. enter the prepared dashboard and inspect corridor evidence;
2. review a recommendation and create an inspection order;
3. capture prepared inspection evidence and retry synchronization;
4. review inspection evidence and generate a summary;
5. prepare and review a non-executable mowing plan;
6. run a simulated mowing rehearsal and synchronize post-service evidence;
7. review evidence, exception, and CSV export;
8. verify common authentication, authorization, conflict, validation, and dependency
   failures;
9. perform dashboard keyboard, zoom, reduced-motion, and assistive-technology checks;
10. verify mobile airplane-mode, process-death, relaunch, accessibility, and logout
    recovery.

Authenticated browser-to-database journeys and representative-device checks remain
manual. Selecting a new browser/device automation framework is a separate dependency
decision.

## Quality requirements

### Data and geospatial

- immutable raw source and registered SHA-256;
- explicit source/reference/observation date;
- parser, rule, processor, dataset, and model version where applicable;
- explicit CRS and transformation path;
- idempotent import and stable external identifiers;
- quality report for invalid, missing, duplicate, ambiguous, and inferred records;
- no simplified display geometry overwriting the canonical geometry; and
- no demo or simulated record in training or official reports.

### API and workflow

- strict schemas and versioned OpenAPI;
- server-derived actor and cross-road negative tests;
- stable correlation/error contract;
- append-only human decisions and audit events;
- idempotent retry behavior;
- safe dependency failure;
- recoverable pagination for growing queues when implemented; and
- no endpoint that silently promotes field, training, or reporting eligibility.

### Web and accessibility

- keyboard-accessible actions and visible focus;
- one meaningful `main`, skip navigation, landmarks, and unique titles;
- 200% zoom and target viewport checks;
- status conveyed through text/icon as well as color;
- loading, empty, partial, stale, forbidden, and retry states;
- equivalent list access when map tiles fail; and
- source, date, status, and limitations next to estimated or simulated values.

### Mobile

- encrypted user-bound local state;
- stable event/photo identifiers;
- manifest-before-bytes ordering;
- explicit pending, sending, accepted, rejected, and conflict outcomes;
- process restart without silent draft loss;
- no password persistence;
- offline logout uncertainty surfaced to the user; and
- no production release claim based on a debug APK.

## Demonstration rules

The demo environment must use its own database/storage and clearly identify its
environment. Reset and seed procedures may create prepared/simulated data only when
the status is visible and reproducible. A demo must not require production secrets.

Recommended narrative:

1. identify source date and geometry limitations;
2. show the 100 m segment and separate zone;
3. inspect satellite or historical evidence and its quality;
4. explain a recommendation and confidence limitation;
5. record an explicit human decision;
6. demonstrate prepared/offline evidence flow;
7. show append-only review/history and non-official export; and
8. close with unavailable operational capabilities and next gates.

Do not demonstrate a prepared mowing plan as actual dispatch or completion.

## Pilot and evaluation

The original manual proposed a provisional pilot corridor. That proposal is not an
approved operational area. A future academic or controlled pilot must record:

- versioned AOI and authoritative geometry status;
- source licenses and observation window;
- baseline process used for comparison;
- inclusion/exclusion criteria;
- field safety, privacy, device, and retention procedures;
- responsibility for annotation, adjudication, intervention, and incident response;
- technical and operational metrics with uncertainty; and
- go/no-go authority and rollback conditions.

Candidate metrics include coverage with usable evidence, inspection routing rate,
human correction rate, per-class precision/recall and IoU, spatial/temporal holdout
performance, synchronization recovery, time-to-review, and provenance completeness.
No target becomes official until it is documented and approved for that experiment.

## Decisions and blockers

### Project decisions Rafael may document

For the academic repository, Rafael can approve scope, ordering, terminology,
demonstration parameters, and technical experiments when they do not claim external
authority. The rationale and limitations should be versioned.

### Decisions with accepted academic assumptions

- ZENIT is an academic/student project brand with no direct Motiva relationship,
  sponsorship, authorization, or brand license. The project may use ZENIT-only
  tokens and copy for demonstration while avoiding official Motiva logos, assets,
  colors, slogans, endorsement language, and affiliation claims. See
  [ADR-0069](../decisions/ADR-0069-academic-brand-boundary.md).

### Decisions that still need an appropriate owner or explicit project assumption

- official permission to use Motiva logo, colors, branded assets, endorsement
  language, or partner-facing identity;
- which regulatory/concession instrument applies to a real corridor;
- authoritative road axis, zone boundaries, and ambiguous KMZ attributes;
- source licenses and permitted use of provider imagery;
- operational identity, MFA, recertification, and service-account policy;
- field photo/GPS consent, anonymization, retention, and legal hold;
- device enrollment, loss, revocation, and production app distribution;
- observability data, SLOs, alerts, and incident roles;
- backup locations, encryption, RPO/RTO, restoration owners, and exercises;
- model dataset, compute/dependencies, acceptance, shadow mode, and promotion; and
- any authority to dispatch or report mowing as real.

An academic assumption can unblock a demonstrative design only when it is labeled as
such and does not override law, license, privacy, safety, or a source contract.

## Principal risks

- optical imagery obscured by cloud, shadow, season, or canopy;
- false precision when spectral response is presented as height;
- estimated or misaligned geometry directing attention to the wrong zone;
- historical source dates appearing current;
- ambiguous raw attributes contaminating normalized data;
- prepared/simulated evidence appearing operational;
- compromised credentials, tokens, provider keys, or supply-chain dependencies;
- hostile or privacy-sensitive media entering an unapproved pipeline;
- offline retry/account switching losing or duplicating evidence;
- external map/provider availability, privacy, license, or quota failure; and
- backups, volumes, or green health checks being mistaken for tested recoverability.

Risk treatment is maintained in
[`docs/security/incremental-threat-model.md`](../security/incremental-threat-model.md).

## Definition of Done

A change is complete only when:

- its ticket scope and predecessors were confirmed;
- affected files were reserved and unrelated user changes preserved;
- domain thresholds, zones, human review, provenance, and status labels remain valid;
- code, contract, migration, consumer, and documentation changes stay coherent;
- relevant automated and manual checks have recorded outcomes;
- secrets, personal data, raw sources, and large imagery were not committed;
- accessibility and failure states were considered where visible behavior changed;
- the change was reviewed for security and operational overclaiming;
- limitations and rollback are documented;
- a cohesive English commit was pushed to a ticket branch; and
- a pull request received the required human peer review before merge.

Completion never means that a model or agent has accepted risk on behalf of Motiva,
a regulator, a data owner, a privacy owner, or an operational manager.
