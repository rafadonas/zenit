# ADR-0076: Planet scene download-permission filter

- Status: accepted for capability validation; no Order or download is enabled
- Date: 2026-09-15
- Ticket: PLANET-002
- Predecessor: ADR-0067 and ADR-0075

## Context

Catalog authentication does not prove that a particular scene and asset can be
downloaded. Planet exposes an `assets:download` permission filter for searches,
while Orders, bundles, and delivery have separate permissions and quotas.

## Decision

Extend the backend-only `PSScene` search builder with an opt-in
`PermissionFilter` for `assets:download`. Add `zenit-planet-capabilities`, a
bounded worker command that runs this filtered search and reports only counts,
pagination, and explicit false order/download/operational flags. The existing
catalog command can also enable the filter with
`--require-download-permission`.

The key remains in `PL_API_KEY` on the worker and is never put in a URL,
browser/mobile payload, or log. No scene, asset URL, order ID, response body, or
byte is persisted by this increment.

The same documented development corridor AOI and 2026-08-01 through 2026-08-07
UTC window were validated on 2026-09-15. The filtered catalog returned 13
acquisitions with no next page, while reporting
`order_requested=false`, `download_requested=false`, and
`operationally_eligible=false`.

## Consequences

- A successful filtered search is evidence that matching catalog items advertise
  the account's scene-download permission for the selected AOI/time window.
- An empty result can mean no clear/available item or missing permission; it is
  not a license or quota approval.
- Product bundle selection, order creation, area quota, checksum/lineage,
  storage, and human approval remain separate tickets before a download.
