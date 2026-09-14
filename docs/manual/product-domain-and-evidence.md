# Product, domain and evidence

This chapter maintains the product, source, domain, workflow, and intelligence
content from chapters 1-8 of the original master manual.

## Product purpose

ZENIT helps an academic team demonstrate how road-vegetation evidence can become
an explainable, auditable recommendation and then a human-reviewed workflow. It
connects satellite metadata and products, road geometry, historical classifications,
field evidence, and operational context without claiming that remote sensing alone
measures vegetation height or authorizes an intervention.

The intended users are:

- managers, who review recommendations and prepared evidence;
- supervisors, who review allowed cases and inspect histories;
- field users, represented by the offline-first Android demonstration;
- maintainers and reviewers, who preserve contracts, data status, and auditability;
  and
- academic evaluators, who need a reproducible input-to-output narrative.

The current implementation does not represent a real concession operation. It
contains local identities, prepared orders, simulated locations, simulated mowing
rehearsals, and non-official summaries. Those labels are part of the domain contract,
not presentation disclaimers that may be removed.

## Problem and value hypothesis

The supplied FIAP/Motiva challenge describes vegetation monitoring as a recurring
conservation problem that can benefit from remote sensing, data analysis, and AI.
The project addresses five connected difficulties:

1. long corridors are expensive to inspect uniformly;
2. fixed schedules do not express current evidence or uncertainty;
3. images, historical classifications, inspections, and services are difficult to
   relate spatially and temporally;
4. a recommendation can lose its reason, source, or reviewer while moving between
   systems; and
5. a visually convincing map can overstate the age, quality, or meaning of evidence.

The academic value hypothesis is that a traceable chain of evidence can prioritize
human attention and make decisions more reviewable. Any claimed cost, safety,
productivity, or environmental gain requires a defined baseline and measured pilot;
the current repository does not prove those gains.

See the [FIAP/Motiva challenge companion](../reference/fiap-motiva-challenge-brief.md)
for the source brief without converting its promotional figures into ZENIT KPIs.

## Source inventory and authority

The initial source set includes challenge documents, two regulatory/concession
references, spreadsheets, kilometer markers, mowing-classification polygons, and a
technical satellite API guide. The immutable inventory, sizes, and checksums are
maintained in [`docs/data-quality/initial-audit.md`](../data-quality/initial-audit.md).

Important interpretation limits:

- the two spreadsheets are separate file versions with an internal reference date
  of 2025-03-28, not a confirmed time series or current condition;
- `classificacao_rocada.kmz` contains an inconsistent inferred attribute mapping;
- the marker-derived road axis is estimated, not official dispatch geometry;
- contractual references belong to their specific instruments and must not be
  merged silently; and
- the satellite guide is a dated technical reference, not an observation or a
  credential source.

Every import or derived product should retain the source filename or identifier,
SHA-256, import/run time, parser or processor version, original and processing CRS,
reference/observation time, data status, quality result, and lineage to downstream
artifacts.

## Spatial model

### Analysis unit

The analytical unit is a versioned 100 m road segment. Each segment is subdivided
into independent zones:

- `left`;
- `right`;
- `median`; and
- `special`.

The same segment can therefore have different evidence, thresholds, confidence,
recommendations, and histories per zone. Implementations must not collapse both
sides or infer a median where none exists. Special areas require explicit geometry
or configuration rather than visual guesswork.

Operational grouping into a longer work order may be useful, but grouping never
changes the canonical 100 m evidence unit. The prepared workflow currently keeps
source segment-zone identifiers and three planned points per inspection order.

### Coordinate reference systems

- preserve original KML/KMZ coordinates in WGS 84 (`EPSG:4326`);
- construct metric road buffers, lengths, and segment operations in SIRGAS 2000 /
  UTM zone 23S (`EPSG:31983`) for the current study area;
- transform provider request geometries explicitly to the CRS required by that
  provider; and
- record every inferred or transformed CRS in lineage.

The estimated axis must remain labeled `estimated` until an authoritative geometry
is validated. Its existence is sufficient for a local demonstration, not for field
dispatch.

## Vegetation thresholds and historical classes

The project preserves two separate concepts: an intervention threshold and a
historical height class.

| Context | Threshold used by ZENIT | Meaning |
| --- | ---: | --- |
| General road-domain vegetation | 30 cm | General configured threshold derived from the supplied references. |
| Special/operational areas | 10 cm | Stricter configured threshold for explicitly identified areas. |

Historical source classes remain:

- N1: below 10 cm;
- N2: from 10 cm through 30 cm; and
- N3: above 30 cm.

These boundaries must be represented consistently in code and tests. A historical
class is not a current measurement. A satellite vegetation index is not a height
measurement. A cover type such as tree or grass is not a severity class.

The [ANTT](../reference/antt-per-volume-i.md) and
[ARTESP](../reference/artesp-conservation-annex.md) companions retain the source
context for vegetation limits, coverage, monitoring, and evidence expectations.

## Evidence and data states

Evidence should be interpreted on independent axes:

| Axis | Examples | Question answered |
| --- | --- | --- |
| provenance | source file, provider, observation, photo, human review | Where did it come from? |
| data status | real, estimated, prepared, simulated, inconclusive | What kind of claim can it support? |
| quality | accepted, limited, rejected, cloudy, incomplete | Is it usable for this purpose? |
| temporal status | observed at, reference date, valid until, stale | When was it applicable? |
| review status | pending, accepted, adjusted, rejected, superseded | What did a human decide? |
| eligibility | training, field execution, official reporting | What may it be used for? |

No single confidence score replaces these axes. In particular, confidence must not
be presented as the exact probability that vegetation has a specific height.

## Recommendation workflow

The initial analytical baseline is explainable and rule-oriented:

1. resolve a versioned segment and zone;
2. load eligible evidence with source time and quality;
3. apply a versioned quality rule and threshold configuration;
4. produce a recommendation and human-readable explanation;
5. show uncertainty and limitations;
6. route low-confidence or conflicting evidence to inspection; and
7. record an immutable human decision without overwriting the original output.

Possible recommendation outcomes include monitoring, inspection, or a mowing-related
planning recommendation. None is a field authorization. A reviewer can accept,
reject, or adjust only within the versioned policy and road-scoped role enforced by
the server.

## Prepared inspection workflow

The repository implements an end-to-end prepared inspection path:

1. a reviewed recommendation becomes a prepared inspection order;
2. the order retains its source review, policy, road, segment, zone, and rationale;
3. three planned points are delivered to the mobile application;
4. encrypted local drafts and a persistent sync queue survive offline operation;
5. manifest-first photo synchronization verifies identifiers, size, media type, and
   SHA-256 before encrypted object storage;
6. human photo review records quality and ruler visibility;
7. a prepared inspection summary is generated only after required evidence gates;
8. a post-inspection proposal remains non-operational and requires human review; and
9. CSV export retains provenance and non-official labels.

The mobile client is an offline-capable demonstration. GPS/location and field states
that are simulated must remain explicit. Failure, conflict, retry, and logout
uncertainty are visible rather than silently discarding unacknowledged drafts.

## Prepared mowing workflow

The repository also demonstrates a non-executable mowing-planning and rehearsal
path:

1. an eligible reviewed post-inspection proposal can create a prepared mowing order;
2. resource, weather, safety, and approval artifacts remain prepared and unassigned;
3. the mobile application can read the plan but cannot promote it to field execution;
4. a simulated rehearsal records immutable confirm/start/pause/resume/finish events;
5. post-service heights and photo manifests are simulated and unverified;
6. photo review, summary, and threshold-exception decisions remain human and
   append-only; and
7. exports are explicitly ineligible for official reporting.

The following properties must never be inferred or toggled by a client:

- `authorizes_field_work`;
- `operational_approval_satisfied`;
- `eligible_for_field_execution`;
- `eligible_for_model_training`; and
- `eligible_for_official_reporting`.

## Satellite evidence

The provider-neutral discovery boundary supports:

- Sentinel-2 L2A catalog discovery and validated statistical/process experiments;
- CBERS-4A catalog discovery through the INPE BDC/STAC boundary; and
- PlanetScope `PSScene` metadata discovery without ordering or downloading assets.

The current validated Sentinel artifact is a small, checksum-bound prepared NDVI
preview. It is not a complete cached scene and does not establish vegetation height.
The dashboard exposes persisted observation metadata and warnings without storage
URIs or provider credentials.

Every optical source is sensitive to acquisition date, cloud and shadow, accepted
pixel coverage, geometric alignment, season, and sensor/product differences. Sentinel,
CBERS, and Planet products are not interchangeable measurements.

## Vegetation intelligence maturity

The desired cover taxonomy distinguishes at least:

- `unknown`;
- `grass_herbaceous`;
- `shrub`;
- `tree`;
- `mixed`; and
- `non_vegetation`.

It must be versioned and accompanied by source, method, observation time, quality,
visibility/occlusion, confidence band, review status, and limitations. Cover type
must not derive N1/N2/N3 and must not be inferred from NDVI color alone.

The maturity path is:

1. manual/rule-based labels with explicit uncertainty;
2. reproducible offline baseline using non-demo, licensed, versioned data;
3. spatial and temporal holdouts with per-class error analysis;
4. shadow mode invisible to operational decisions; and
5. reviewed assistance only after a formal gate.

Model outputs need a model version, dataset version, run inputs, processor version,
quality context, and rollback target. Human corrections become candidate feedback;
they do not automatically retrain or promote a model.

## Evidence reuse and reporting

Field or remote-sensing evidence may be reused only when purpose, location, time,
quality, and version remain compatible. A later report must not silently combine
different dates, sensors, zones, or review states. Before/after comparisons need
explicit timestamps and comparable methods.

Official reporting and operational effectiveness remain unavailable. Current exports
exist to demonstrate traceability and must preserve prepared/simulated status,
provenance, limitations, and human decisions.
