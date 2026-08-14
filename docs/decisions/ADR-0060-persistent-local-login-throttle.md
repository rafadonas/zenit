# ADR-0060: Persistent local login throttle

- Status: accepted
- Date: 2026-08-14

## Decision

Protect the provisional local password endpoint with a PostgreSQL-backed,
versioned throttle. Key state and append-only events by an HMAC-SHA256 digest
of the normalized login identifier using the authentication secret. Never
persist the submitted identifier, password, or upstream error detail in the
throttle tables.

Allow five failed attempts in a rolling 15-minute window by default, then block
that identifier for 15 minutes. Serialize state transitions with a PostgreSQL
transaction advisory lock. Record `failed`, `blocked`, and `succeeded` events
with the policy version and request correlation ID. A successful login clears
the mutable throttle state but not its audit events.

Return the same HTTP 429 response and `Retry-After` header for known and unknown
identifiers. Keep the limit, window, block duration, and policy version bounded
and configurable.

## Consequences

The control survives API restarts and applies consistently across API
processes. It reduces repeated password guessing and expensive Argon2 work
without storing another copy of an email address. Rotating the authentication
secret intentionally makes prior identifier digests unlinkable to new attempts.

An attacker can temporarily block a known identifier, and historical security
events still require an approved retention policy. This local control is not a
replacement for corporate identity, adaptive risk controls, password recovery,
session revocation, perimeter rate limiting, or centralized security monitoring.
