# ADR-0057: Dependency-aware API readiness

- Status: accepted
- Date: 2026-08-14

## Decision

Make `GET /health` a fail-closed readiness endpoint for the P0 deployment. Run
bounded PostgreSQL and MinIO checks concurrently and return HTTP 200 only when
both required dependencies respond. Return the standard correlated HTTP 503
error when either check fails without exposing its exception or configuration.

Report the queue as `not_configured` and non-required. The MVP has no broker or
independent network worker, and introducing one solely for a health response
would contradict the modular deployment decision in ADR-0001. Keep the probe
timeout configurable and bounded through runtime settings.

Require the tracked stack smoke verifier to validate each readiness field, not
only the aggregate `status`. Use the same endpoint for the Compose API
healthcheck so initial dashboard startup follows database and storage
availability.

## Consequences

An API process can no longer appear ready while PostgreSQL or MinIO is
unreachable. Fresh-stack and CI checks exercise the actual dependency path, and
operators receive a correlation identifier for sanitized diagnostics.

The endpoint is not a data-quality, backup, restoration, policy, or operational
authorization check. A separate queue becomes required only if a future
approved architecture introduces a broker or independently deployed worker.
