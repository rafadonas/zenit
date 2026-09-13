# API-001 — Queue view models and pagination analysis

Status: analysis complete; no API contract or consumer change is included in this
work package.

Assessed revision: `a96c1de` (`main`, 2026-09-13).

## Objective and method

This analysis identifies API changes that would reduce measured consumer or query
complexity. It covers dashboard and mobile queue consumers, their OpenAPI collection
contracts, and PostgreSQL reader query shapes. It does not define a new endpoint,
choose an architecture, or authorize operational behavior.

Measurements combine:

- static call-path inspection in the dashboard and mobile clients;
- field counts and pagination metadata from `contracts/openapi.json`;
- SQL execution counts derived from the current PostgreSQL readers; and
- read-only HTTP measurements against the local prepared/demo stack.

The local snapshot is not production evidence or a load test. Its records remain
prepared or simulated as labeled by their contracts. No protected payload or secret
was read for this analysis.

## Consumer call baseline

Counts below are upstream API calls required for the initial server render or mobile
collection load. Authenticated dashboard counts include `/v1/auth/me`.

| Consumer | Initial API calls | Collections involved | Finding |
| --- | ---: | --- | --- |
| Corridor map (`/`, `/corridor`) | 2 | segments, vegetation map | Both requests use one fixed full-corridor bounding box. Selecting a segment adds one satellite-observation call. |
| Overview | 3 authenticated; 2 anonymous | recommendations, segments, session | Calls are independent and parallel; no cross-collection join is required. |
| Recommendation queue | 2 | recommendations, session | Already one queue call plus authentication. |
| Inspection photo review workspace | 7 | photo-review queue, inspection summaries, post-inspection proposals, mowing rehearsals, mowing post-service summaries, mowing post-service exceptions, session | The page joins six independently truncated 50-item windows in memory. Related state can be absent when it falls outside another collection's window. |
| Mowing photo review queue | 2 | mowing photo-review queue, session | Already one queue call plus authentication. |
| Mowing post-service summary workspace | 3 | summaries, exceptions, session | The page joins two independently truncated windows. |
| Mobile inspection orders | 1 | work orders, `limit=100` | The parser returns items but exposes no continuation path or truncation signal. |
| Mobile prepared mowing plans | 1 | prepared mowing orders, `limit=100` | The parser validates truncation metadata but returns only the items; it cannot request a next page. |

The inspection photo review workspace is the only current dashboard consumer with a
clear call-count and consistency case for a dedicated read model. Combining unrelated
overview data would add coupling without eliminating a material client-side join.

## Collection contract baseline

Every reviewed queue accepts `limit` with a default of 50 and maximum of 100. None
accepts an offset or cursor, and none returns a continuation token.

| Collection | Item fields in OpenAPI | Truncation metadata | Current reader shape |
| --- | ---: | --- | --- |
| Recommendations | 26 | `total_count`, `truncated` | One joined query with `limit + 1`. |
| Inspection work orders | 22 | none | ID query followed by two queries per item: `1 + 2N`; it requests exactly `limit`, so omission is silent. |
| Inspection photo-review queue | 23 | `truncated` | One joined query with `limit + 1`. |
| Inspection summaries | 21 | `truncated` | One joined query with `limit + 1`. |
| Post-inspection proposals | 51 | `truncated` | One joined query with `limit + 1`. |
| Prepared mowing orders | 50 | `truncated` | ID query followed by one aggregate query per item: `1 + N`. |
| Mowing rehearsals | 21 top-level fields plus nested events/evidence | `truncated` | Target query followed by three queries per item: `1 + 3N`. |
| Mowing photo-review queue | 29 | `truncated` | One joined query with `limit + 1`. |
| Mowing post-service summaries | 23 | `truncated` | One joined query with `limit + 1`. |
| Mowing post-service exceptions | 28 | `truncated` | One joined query with `limit + 1`. |

At `limit=50`, the inspection-order reader can execute 101 SQL statements and the
mowing-rehearsal reader 151. At the mobile limit of 100, inspection orders can execute
201 statements and prepared mowing orders 101. These are source-derived upper bounds
for a full page, not timed production benchmarks.

`truncated=true` currently tells a consumer that data was omitted but supplies no way
to recover it. The inspection-order response is weaker: it cannot tell the consumer
that more rows exist.

## Local payload sample

The existing local prepared/demo snapshot returned:

| Request | Result | Response bytes | Local elapsed time |
| --- | ---: | ---: | ---: |
| `GET /v1/recommendations?limit=50` | 2 items | 2,824 | not used as a benchmark |
| `GET /v1/roads/SP021/segments` with the dashboard bounding box | 309 features | 110,487 | 0.09 s |
| `GET /v1/roads/SP021/vegetation-map` with the dashboard bounding box | 642 features | 1,420,703 | 1.62 s |
| first segment's satellite observations | 0 items | 223 | not used as a benchmark |

The map numbers explain a consumer issue, not an endpoint gap: both map APIs already
support bounding-box filtering, while the dashboard server always supplies the fixed
`-46.84,-23.64,-46.72,-23.4` corridor box. Viewport-based requests, cancellation, and
caching belong in the map consumer work. A replacement map endpoint is not justified.

The protected queue payloads were not measured because the local data volume is too
small to support a representative payload or latency conclusion and this analysis did
not use or print development credentials. The 50- and 51-field aggregates are a prompt
to benchmark list projections, not evidence that safety or provenance fields should be
removed.

## Recommended follow-up order

### 1. Remove N+1 reads without changing contracts

Batch-load or aggregate related records for inspection orders, prepared mowing orders,
and mowing rehearsals. Preserve response schemas, actor-scoped road authorization,
ordering, safety flags, provenance, and prepared/simulated labels.

Acceptance evidence should show a constant number of SQL executions for a full page:
at most three for inspection orders and rehearsals, with query plans and representative
seeded volumes recorded. Contract tests must remain unchanged.

This is the lowest-risk performance improvement because it requires no consumer
migration.

### 2. Add recoverable, stable pagination to existing queues

Define an opaque keyset cursor over an immutable ordering tuple such as creation time
and stable identifier. The exact tuple and direction must be fixed in an ADR and the
OpenAPI contract; consumers must not construct or inspect cursors.

Start with the two mobile collections:

1. inspection work orders, which currently truncate silently; and
2. prepared mowing orders, which expose an unusable truncation flag.

Then migrate the growing dashboard queues. During a compatibility window, retain
`limit`, existing `items`, and current safety metadata while adding a continuation
field such as `next_cursor`. Consumers must continue until the cursor is absent and
must handle retries idempotently.

Acceptance evidence must demonstrate no gaps or duplicates while newer records are
inserted, deterministic replay of a cursor, authorization on every page, and an
explicit response for invalid or expired cursors. Offset pagination is not recommended
because concurrent queue inserts can shift boundaries.

### 3. Prototype one case-oriented inspection review view model

Benchmark a read-only projection rooted in an inspection work order for the inspection
photo review workspace. It should provide only the list/workspace state currently
joined from photo review, inspection summary, proposal, mowing rehearsal, post-service
summary, and exception collections. Detail and mutation endpoints remain separate.

The projection is justified only if a representative seeded benchmark confirms that it:

- reduces the authenticated page from seven upstream calls to at most two, including
  session loading;
- returns related state from the same root case and pagination snapshot;
- has a materially smaller payload than downloading six full aggregates; and
- preserves road-scoped RBAC, human decisions, immutable audit references, rule/model
  versions, provenance, and explicit real/estimated/simulated/prepared/inconclusive
  labels.

The route name and schema are intentionally undecided. An ADR and OpenAPI change are
required before implementation, followed by an atomic dashboard migration. A generic
"dashboard" endpoint is not recommended.

For the mowing post-service summary workspace, first measure whether projecting the
latest exception state in the existing summary collection is sufficient. A separate
endpoint is not yet justified.

## Required delivery controls for API changes

Any follow-up that changes a public response must include, in the same cohesive change:

- an ADR describing ordering, cursor stability, snapshot semantics, compatibility,
  authorization, and failure behavior;
- an updated versioned OpenAPI contract and contract tests;
- migrated dashboard/mobile parsers and pagination behavior;
- representative query-count, payload-byte, and latency baselines before and after;
- preservation tests for human approval, audit trail, provenance, data-status labels,
  and the rule that AI never authorizes mowing; and
- a rollback path that does not lose or relabel evidence.

No production threshold or Motiva value should be invented to set a payload budget.
Budgets should be chosen only after representative measurements are recorded.

## Decision from API-001

API-001 recommends query batching and recoverable keyset pagination as concrete
follow-up work. It recommends a single inspection-case view-model prototype only after
a representative benchmark. It rejects a new map endpoint and broad dashboard
aggregation on the current evidence.

No ADR, OpenAPI schema, database migration, endpoint, or consumer was changed here.
