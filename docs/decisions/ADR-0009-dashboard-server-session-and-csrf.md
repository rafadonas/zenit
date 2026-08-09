# ADR-0009: Dashboard server session and CSRF boundary

- Status: accepted
- Date: 2026-08-08

## Context

ADR-0008 introduced short-lived bearer authentication and road-scoped review
authorization at the API. Exposing that bearer token to browser JavaScript or
accepting state-changing browser requests without a CSRF boundary would make
dashboard decision controls unsafe. The public recommendation queue must remain
useful without creating an implicit authorization path.

## Decision

Keep the recommendation queue publicly readable. Authenticate dashboard users
through a Next.js server route and store the short-lived API bearer token only
in an `HttpOnly`, `SameSite=Strict` cookie. Do not return it to client
JavaScript, browser storage, or decision form fields. Resolve the current user
and road roles server-side through `GET /v1/auth/me` before rendering controls.

Proxy logout and recommendation decisions through Next.js server routes. Every
state-changing dashboard request must provide both an exact configured
`Origin` and a random 256-bit CSRF token matching a separate strict cookie.
Compare CSRF values in constant time. Allowlist and validate form fields before
building the API request; never forward a client-supplied actor. The API remains
the authorization authority and rechecks the active account, scoped role,
policy, target, and idempotency contract.

Render decision controls only for a road that appears in the user's current
manager/supervisor assignments. When a prior review exists, submit its immutable
identifier as the event being superseded. Logout and an API authentication
failure clear the session cookies.

Permit non-secure cookies only for local HTTP development. Staging and
production configuration must use an HTTPS public origin and secure cookies;
invalid combinations fail closed at startup/request evaluation. Introduce no
new production dependency for this boundary.

## Consequences

- The bearer credential is unavailable to ordinary browser JavaScript and is
  never accepted from a review form.
- Cross-site mutations require defeating exact-origin, strict-cookie, and CSRF
  checks together; the API still enforces RBAC independently of the UI.
- An unauthenticated or unassigned user can inspect the queue but cannot render
  or successfully call a decision control.
- The local MVP still lacks corporate identity, refresh/revocation sessions,
  password reset, login rate limiting, and a complete content-security policy.
  It is not approved for direct internet exposure.
- Review decisions remain append-only audit events. They do not create a work
  order, silently approve mowing, or authorize any field activity.
