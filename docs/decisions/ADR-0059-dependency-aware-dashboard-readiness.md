# ADR-0059: Dependency-aware dashboard readiness

- Status: accepted
- Date: 2026-08-14

## Decision

Expose a public, read-only `GET /api/health` route from the dashboard. Use a
two-second server-side request to the configured API `/health` endpoint and
return HTTP 200 only when the API reports the exact required PostgreSQL, MinIO,
and optional queue readiness contract. Return sanitized HTTP 503 JSON for
network failures, upstream errors, timeouts, or malformed readiness data.

Point the Compose dashboard healthcheck at this route. Keep the separate stack
smoke verifier responsible for loading and identifying the fully rendered
corridor and login pages.

## Consequences

An already running Next.js process becomes unhealthy when its server-side API
connection or the API's required dependencies remain unavailable. Compose can
no longer report the dashboard healthy solely because its HTTP listener is
running. The probe is lightweight and does not repeatedly load the complete
segment collection.

The route exposes no internal error details, credentials, or business data. It
does not verify source quality, authenticate a user, exercise browser
hydration, or authorize field activity. Compose health status also does not
automatically restart one service merely because another service is unhealthy.
