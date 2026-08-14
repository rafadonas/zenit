# ADR-0053: Versioned OpenAPI contract

- Status: accepted
- Date: 2026-08-14

## Decision

Generate `contracts/openapi.json` directly from the FastAPI application and
track its deterministic, sorted representation in the repository. CI runs the
exporter in check mode and fails when application routes or models differ from
the reviewed artifact.

The repository validator requires OpenAPI 3.1.0, the MVP API identity, a public
health endpoint, `/v1` prefixes for all application routes, unique operation
identifiers, tags, and response declarations. It also rejects known local
database credentials, authentication secrets, and media encryption keys.

## Consequences

API contract changes become explicit reviewable diffs and cannot silently ship
without updating the versioned artifact. The JSON contains interface metadata
only; it does not include source data, runtime credentials, operational
evidence, or authorization to execute field work. Updating the artifact does
not replace endpoint tests, database migration checks, or HTTP smoke tests.
