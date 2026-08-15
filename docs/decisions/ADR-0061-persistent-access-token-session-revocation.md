# ADR-0061: Persistent access-token session revocation

- Status: accepted
- Date: 2026-08-14
- Supersedes: session-revocation limitations recorded in ADR-0009 and ADR-0060

## Decision

Register every locally issued access token as an immutable PostgreSQL session
identified by the JWT `jti`. Persist the user, issuer, audience, issuance and
expiry timestamps, and request correlation ID without storing the encoded token.
Reject otherwise valid JWTs when their session is missing, expired, or has an
append-only revocation event.

Expose `POST /v1/auth/logout` to append one `user_logout` revocation per session.
Make repeated revocation idempotent. The dashboard forwards its server-held
bearer token before clearing strict cookies. The Android client attempts remote
revocation before clearing local access, but logout remains available offline
and explicitly reports when remote revocation could not be confirmed.

## Consequences

Logout invalidates a captured token across API processes without waiting for its
30-minute expiry. Emission and revocation remain auditable through correlation
IDs, and neither table contains passwords or reusable bearer credentials.

Deploying this change intentionally invalidates tokens issued before migration
`0039`, because they have no persisted session. Offline Android logout can only
clear local access immediately; an unreachable server cannot record revocation,
so the token remains usable until expiry if it was copied elsewhere.

This control does not provide corporate identity, refresh tokens, password
recovery, administrative session termination, device attestation, or centralized
security monitoring.
