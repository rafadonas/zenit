# ADR-0071: Dashboard guided login and safe return

- Status: accepted
- Date: 2026-09-14

## Context

The dashboard already kept bearer tokens in strict server-managed cookies,
validated request origins, and preserved the API login throttle. The login page,
however, did not announce an in-progress request or prevent a repeated submission.
It also always returned a password login to the recommendation queue, so an
expired-session recovery could not safely preserve an intended dashboard page.

## Decision

Keep the existing server-side session, origin, CSRF, throttle, and revocation
boundaries. Add a client-side form state only for interaction feedback: disable
the controls during submission and announce that access and roles are being
loaded. Never expose, copy, or persist the bearer token in client code or browser
storage.

Present the local/demo environment and profile-loading state before entry. Map
the small allowlist of public error/status query values to generic Portuguese
messages, and ignore every unknown value so upstream details cannot be reflected.

Accept an optional `return_to` form value, but redirect only to an allowlisted
dashboard page with an optional query string. Reject external, encoded API,
login, fragment, control-character, malformed, and unknown destinations and use
the authenticated recommendation queue as the fallback.

## Consequences

- Keyboard and no-JavaScript form submission remain available.
- Repeated submission is visibly blocked while a request is in progress.
- Session expiry has a clear recovery instruction and can preserve an explicitly
  supplied safe dashboard destination.
- Redirect validation must be updated when a new post-login dashboard page is
  intentionally introduced.
- This remains a local academic identity flow, not a production IdP, MFA,
  password-recovery, or corporate-session implementation.
