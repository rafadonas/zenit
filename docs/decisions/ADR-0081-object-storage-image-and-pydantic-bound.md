# ADR-0081: Pinned object-storage image and pydantic bound for CI

- Status: accepted
- Date: 2026-10-20

## Context

On 2026-10-19 two environmental changes broke CI without any code change. The
last green `main` run was on 2026-09-16.

- Python dependencies are lower-bounded only. A fresh install resolved
  pydantic 2.14, which no longer emits the decimal-string `pattern` constraints
  (for example `height_cm` and `applicable_threshold_cm`), so
  `scripts/export_openapi.py --check` reported a stale contract. FastAPI 0.150
  with pydantic 2.13.5 still reproduces the tracked contract exactly, so the
  drift comes from pydantic, not FastAPI.
- `quay.io/minio/minio` and `docker.io/minio/minio` now return 401 to anonymous
  pulls, `bitnami/minio` returns 404, and the upstream `minio/minio` repository is
  archived. The `compose-smoke` job could no longer start the stack.

## Decision

Bound pydantic to `>=2.11,<2.14` in `pyproject.toml`. Lift the bound only in the
same change that reviews and regenerates `contracts/openapi.json`.

Replace the MinIO image with
`docker.io/bitnamilegacy/minio:2025.4.22`, pinned by digest. It is the same
MinIO release the stack used before (2025-04-22). Bitnami's entrypoint runs as
uid 1001, stores data in `/bitnami/minio/data`, and disables the console by
default, so Compose enables it on port 9001. The healthcheck calls
`/minio/health/ready` with the bundled `curl`. The API readiness probe and
object-storage client are unchanged.

## Consequences

- The OpenAPI contract and the local stack are reproducible again.
- The Bitnami legacy image is frozen and receives no security updates. That is
  acceptable for the academic MVP and CI only, not for production. Replacing it
  with a maintained S3-compatible server is a follow-up and needs its own
  decision.
- Existing local `minio-data` volumes that were written by the root-run upstream
  image may not be writable by uid 1001. Run `docker compose down --volumes` to
  recreate them. This deletes local development object data only.
