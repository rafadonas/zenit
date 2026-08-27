# ADR-0062: Local opaque-origin login navigation

- Status: accepted
- Date: 2026-08-27

## Context

ADR-0009 requires exact-origin checks for state-changing dashboard requests.
Chrome can nevertheless serialize the `Origin` header as the opaque value
`null` for a same-origin HTML form navigation under a restrictive referrer
policy. In the local dashboard this caused the login route to return `403
Cross-origin login rejected`, even though the browser reported a same-origin
document navigation to `localhost`.

Treating every opaque origin as trusted would weaken the login-CSRF boundary.
Redirecting with the container's request URL is also incorrect because the
server can see an internal listener address such as `0.0.0.0` instead of the
browser-visible host.

## Decision

Keep exact-origin validation as the default. The dashboard login route may
accept `Origin: null` only when all of the following are true:

- the application environment is `development` or `test`;
- the request `Host` or forwarded host resolves to a loopback, `.localhost`, or
  private-network hostname;
- `Sec-Fetch-Site` is `same-origin`;
- `Sec-Fetch-Mode` is `navigate`; and
- `Sec-Fetch-Dest` is `document`.

This exception applies only to the server-side login form route. It does not
apply in `demo`, staging, or production and does not relax CSRF/origin checks on
logout, recommendation decisions, or other mutations. Cross-site or incomplete
Fetch Metadata fails closed.

For an accepted opaque-origin navigation, build the post-login redirect from
the validated request host rather than the internal request URL. Continue to
store the API token only in the existing `HttpOnly`, `SameSite=Strict` cookie.

## Consequences

- Local Chrome form login works when it emits the opaque origin value.
- An opaque origin alone is insufficient: local host, environment, and Fetch
  Metadata checks must all pass.
- Production retains the exact public-origin requirement from ADR-0009.
- Local reverse proxies must preserve `Host` or set trusted forwarded host and
  protocol headers for browser-visible redirects.
