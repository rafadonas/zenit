# ADR-0063: Fixed local dashboard identity per port

- Status: accepted
- Date: 2026-09-02

## Context

The local demonstration needs simultaneous access to the screens of the
prepared manager and supervisor without repeatedly completing the password
form. Browser cookies are scoped to a host rather than a TCP port, so two
dashboard instances on `localhost` would overwrite each other's session unless
their cookie names were distinct.

Removing API identity checks would destroy actor attribution, road-scoped RBAC,
append-only review provenance, and the human-approval boundary adopted in
ADR-0008 and ADR-0009.

## Decision

Run two instances of the same dashboard image in the local Compose stack. Port
`3000` is fixed to the prepared manager email and port `3002` is fixed to the
prepared supervisor email. Give each instance distinct session and CSRF cookie
names.

When a browser without that instance's cookie requests a page, the dashboard
obtains a short-lived API token through a server-to-server fixed-session
endpoint and stores it in the existing `HttpOnly`, `SameSite=Strict` cookie.
The endpoint requires a dedicated shared secret, is omitted from OpenAPI, and
fails closed unless explicitly enabled in development, test, or demo. It looks
up an existing active user; it never creates or promotes an account. Issued
tokens are registered in the existing persistent session store, and all API
authorization and append-only actor attribution remain unchanged.

The ordinary password login remains available when fixed-session configuration
is absent. Staging and production reject fixed-session mode during settings
validation.

## Consequences

- Local users can open both dashboards without entering passwords.
- Every action is still attributed to the active user fixed to that port and is
  limited by that user's current road roles.
- Anyone who can reach a fixed dashboard port can act as that identity. The
  mode is therefore unsuitable for internet exposure, shared production
  networks, or official operation.
- Existing manager and supervisor accounts must be created before their fixed
  dashboards can obtain sessions.
- Logout or expiry is followed by automatic creation of another short-lived
  session on the next page navigation.
- This decision does not weaken the rule that AI output and recommendation
  review never silently authorize mowing or field work.
