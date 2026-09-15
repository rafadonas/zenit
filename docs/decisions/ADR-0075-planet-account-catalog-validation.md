# ADR-0075: Planet account and catalog validation

- Status: accepted for bounded catalog discovery; download/operations remain blocked
- Date: 2026-09-15
- Ticket: PLANET-001
- Predecessor: ADR-0067

## Context

The backend-only Planet foundation needs an account check before any later
planning or acquisition work. A configured key alone does not prove that the
account can order a product, download a scene, use a particular asset, or train
an academic model with it.

## Decision

Validate the configured `PL_API_KEY` through the existing `PSScene` quick-search
flow, using only the documented development corridor AOI
`[-46.80, -23.55, -46.76, -23.50]` and the bounded UTC window
`2026-08-01` through `2026-08-07`. Keep the key in the backend environment and
send it only in the `Authorization: api-key ...` header. Do not persist the
response, expose scene identifiers, request an Order, fetch an asset, or mark a
scene operational.

The validation succeeded on 2026-09-15 with 13 catalog acquisitions and no next
page. The command reported `download_requested=false` and
`operationally_eligible=false`.

## Consequences

- Catalog authentication and the selected collection/AOI/date filter are usable
  for the account at validation time.
- The result is not evidence of current vegetation condition and does not grant
  download, tile, licensing, quota, or model-training approval.
- The next Planet tickets must separately record a product/asset decision,
  license and consent scope, area quota, cost guard, persistence/checksum plan,
  and human approval before any bytes are downloaded.
