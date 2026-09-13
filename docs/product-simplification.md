# Product simplification audit

Date: 2026-09-09

## Diagnosis

The repository has a reliable technical foundation, but its presentation layer
exposes the implementation history instead of the product story. The previous
manager entry point opened a dense review queue containing policy versions,
internal identifiers, repeated safety warnings, and several controls at once.
That is useful for engineering validation, but unsuitable as the first screen
of an academic demonstration.

The simplification target is one visible narrative:

```text
Map and satellite evidence
-> segment analysis
-> human decision
-> field inspection
-> result and history
```

This work does not weaken approval, audit, provenance, RBAC, or simulation
boundaries.

## Keep

- FastAPI application contracts and road-scoped authorization.
- PostgreSQL/PostGIS schema and append-only audit history.
- MinIO-compatible object storage and encrypted mobile evidence.
- Domain rules for 100 m segments, separate zones, thresholds, and N1/N2/N3.
- Automated Python, TypeScript, Flutter, OpenAPI, migration, and Compose checks.
- Offline-first mobile synchronization and idempotency contracts.

## Refactor

- Dashboard navigation into the five product stages: overview, map, decisions,
  field, and results.
- Repeated page shells and repeated technical warnings into shared presentation
  components.
- API responses into concise dashboard view models before rendering.
- Demo seed orchestration and reset/start commands into one documented path.
- Active documentation so current migrations, routes, and validation records
  cannot drift silently.

## Rewrite

- The manager landing page as a product overview rather than a raw work queue.
- The running-stack smoke check around the fixed-session dashboard flow.
- The presentation script around one representative segment and one decision.
- Dense review cards so the primary decision is visible before audit detail.

## Remove from the main journey

These elements remain available in details or audit views; they are not deleted:

- UUIDs, processor versions, and policy identifiers on first-level cards.
- Repeated paragraphs describing the same non-operational boundary.
- Separate top-level navigation entries for every internal evidence queue.
- Experimental or future capabilities that are not needed to explain P0.

## Increment plan

1. Introduce the simplified manager overview and make it the local entry point. **Done.**
2. Extract one shared application shell and reduce the primary navigation. **Done.**
3. Redesign recommendation review around progressive disclosure. **Done.**
4. Combine field evidence queues into one field workspace.
5. Consolidate results, history, and limitations into the closing view.

The map stage now uses a real cartographic base and the imported historical
vegetation polygons. It remains explicitly limited to SP-021 monitoring data;
surrounding roads belong to the base map and do not imply ZENIT coverage.

Each increment must keep the old routes functional until its replacement is
verified. No raw data, migrations, audit events, or operational safeguards are
removed as part of visual simplification.
