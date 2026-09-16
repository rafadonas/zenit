# ADR-0085: Authenticated tile proxy, closed by default

- Status: accepted as a closed capability; serving tiles depends on licence and privacy approvals
- Date: 2026-09-15
- Ticket: PLANET-006
- Predecessors: ADR-0066, ADR-0067, ADR-0081, ADR-0084

## Context

ADR-0067 requires a controlled backend proxy before any Planet tile reaches a
browser, because the provider key may not be exposed and the account quota must
stay bounded. MAP-01 in the threat model adds that external tiles reveal the
viewer's address and location context to the provider.

The tile licence (rows L3 and L6 of the licence register) and the viewer-address
decision (D6 of the privacy baseline) are not approved.

## Decision

Add `GET /v1/tiles/{provider}/{z}/{x}/{y}.png` behind `TILE_PROXY_ENABLED`,
which defaults to false. While disabled, unknown, or configured without the
provider attribution, the route answers `404` and never contacts the provider.

When enabled it requires an authenticated session, validates the provider
against an allowlist and the coordinates against the zoom bound, applies a
sliding per-user rate limit, serves from a bounded local cache with a
configurable TTL, and returns the provider attribution in a response header. The
provider key is used only inside the backend request.

Rate limiting is per authenticated user and never per address, so enforcing a
quota does not require storing viewer addresses. OpenStreetMap stays outside the
proxy: its community policy does not allow third-party caching without
authorization, so the dashboard keeps loading it directly.

## Consequences

- The capability can be reviewed and tested before any licence exists, without
  being reachable by accident.
- The provider never sees the viewer's address, which is what MAP-01 asks for.
- The cache lives in the process: restarting empties it and several workers keep
  separate copies. That is acceptable for the academic demonstration and is
  recorded as a limitation; a shared cache would need object storage or Redis.
- Switching the dashboard map to the proxy is deliberately not part of this
  ticket: it only makes sense once the licence rows are approved.
