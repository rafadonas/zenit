# ADR-0008: Local MVP identity and versioned recommendation-review policy

- Status: accepted
- Date: 2026-08-08

## Context

The append-only review schema deliberately had no write endpoint because a
client-supplied reviewer identifier would not prove who acted. Sprint 4 needs a
bounded identity and authorization mechanism before managers can accept,
reject, or adjust a recommendation. Corporate identity and the official Motiva
approval policy remain unavailable.

## Decision

Use local email/password identity for the MVP, as the provisional treatment of
project pending item P-07. Store only Argon2 password hashes. Issue short-lived
HS256 JWT access tokens containing a stable user UUID as `sub`, plus issuer,
audience, issued-at, expiry, and token ID claims. The signing secret stays in
runtime configuration and the API rejects the development default in staging
and production. Every authenticated request rechecks that the account is
active; roles are not trusted from token claims.

Scope manager and supervisor roles to the current `road` entity. This is the
narrowest enforceable scope in the existing schema; concession-level RBAC
remains future work after concessions are modelled. Local role assignments and
the initial review policy are explicitly `prepared`, not official Motiva data.

Persist immutable review-policy versions. The initial
`recommendation-review-mvp-v1` version permits a manager or supervisor to record
one review decision and does not require dual review. This choice applies only
to recommendation review; it is a configurable MVP policy, is not an official
approval rule, and has a database constraint that prevents it from authorizing
field work.

Expose `POST /v1/recommendations/{vegetation_analysis_id}/decisions`. The actor
always comes from the verified bearer token. The API hashes the caller's
idempotency key before storage, validates RBAC in the application and database,
and records the policy version with the append-only decision. A correction
inserts a superseding event. Replays return the original result only when actor,
target, and payload match; conflicting reuse is rejected.

Provide a local `zenit-user` bootstrap command that prompts for the password
without echoing it and creates no default account or committed credential.

## Consequences

- Reviewer identity can no longer be supplied or forged in the decision body.
- Passwords, signing secrets, and production reviewer identifiers are not
  fixtures or log fields.
- Disabling an account blocks new authenticated requests even before its JWT
  expires.
- There is no refresh token, self-registration, password-reset, role-management,
  login rate limiting, or corporate identity flow in this increment; the local
  MVP authentication endpoint must not be exposed directly to the internet.
- HTTPS is required outside local development because bearer tokens are not
  encrypted by JWT.
- Dashboard decision controls require the server-side session and CSRF boundary
  adopted in ADR-0009; unauthenticated access remains read-only.
- Work-order authorization and any official single/dual-approval policy remain
  separate future decisions.
