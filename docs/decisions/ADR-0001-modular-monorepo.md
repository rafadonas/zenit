# ADR-0001: Modular monorepo

- Status: accepted
- Date: 2026-08-06

## Context

ZENIT needs an API, geospatial processing, an explainable analysis component, a
web dashboard, a mobile application, shared contracts, and infrastructure. The
MVP is being developed by one project team and must keep cross-component changes
traceable without introducing operational complexity prematurely.

## Decision

Use a modular monorepo. Deployable applications live in `apps/` and `services/`;
shared contracts and configuration live in `packages/`; infrastructure and
migrations live in `infra/`. Modules must expose explicit interfaces and avoid
sharing persistence internals.

The initial API is a single FastAPI deployment. Geospatial and AI workers remain
separate source modules but are not independent network services until workload
or scaling evidence requires that boundary.

## Consequences

- One change can update contracts, implementation, tests, and documentation.
- CI can validate the end-to-end MVP from a single revision.
- Module ownership and dependency direction require active enforcement.
- Components can be extracted later, but extraction is not an MVP goal.
