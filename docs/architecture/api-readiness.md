# API dependency readiness

## Contract

`GET /health` is the public readiness endpoint used by Docker Compose and the
tracked MVP smoke verifier. It returns HTTP 200 only after bounded concurrent
checks confirm that PostgreSQL accepts `SELECT 1` and the configured MinIO
service reports ready through `/minio/health/ready`.

```json
{
  "status": "ok",
  "service": "zenit",
  "version": "0.1.0",
  "environment": "development",
  "checks": {
    "database": {"status": "ok", "required": true},
    "object_storage": {"status": "ok", "required": true},
    "queue": {"status": "not_configured", "required": false}
  }
}
```

The MVP has no broker or independently deployed queue worker. The API therefore
reports the queue explicitly as `not_configured` and non-required instead of
claiming that an absent dependency is healthy. This matches the modular
monorepo boundary in ADR-0001.

If either required dependency is unavailable, the endpoint returns HTTP 503 in
the standard API error envelope. It does not return connection strings,
credentials, hostnames, exception messages, storage paths, or database details.
The response and sanitized warning log share the request correlation ID.

## Timeout and orchestration

`HEALTH_PROBE_TIMEOUT_SECONDS` bounds each required check from 0.1 through 10
seconds and defaults to one second. PostgreSQL and MinIO are checked in
parallel. Compose starts the API only after its dependency containers are
healthy and starts the dashboard only after the API first becomes healthy.

The dashboard relays this dependency boundary through its own public,
read-only `GET /api/health` route. The relay uses a two-second timeout, validates
the API readiness fields, and returns sanitized HTTP 503 JSON when the API is
unreachable or degraded. Compose probes this route, so a later API dependency
failure also marks the dashboard unhealthy. Compose health status does not by
itself stop or restart an already running dependent service.

## Safety boundary

Technical readiness is not data readiness. A successful response does not
approve the estimated road axis, prove that a complete satellite scene exists,
validate field evidence, authorize mowing, promote prepared or simulated data,
or make any artifact eligible for training or official reporting.
