# ADR-0047: Dashboard-generated simulated mowing post-service summary

- Status: accepted
- Date: 2026-08-13

## Decision

Allow authenticated dashboard users to request generation of the existing
simulated mowing post-service summary for a prepared mowing order. The dashboard
submits only a CSRF-checked idempotency key and generation rationale to
`POST /v1/prepared-mowing-orders/{mowing_order_id}/post-service-summary`.

The action is offered only after the dashboard sees three simulated typed
post-service measurements and three effective accepted visual photo reviews
with accepted quality and visible ruler. The API and database remain
authoritative for idempotency, role checks, completeness, aggregate validation,
and non-operational safety flags.

This does not update the map, operational history, official reports, model
training data, execution state, or field authorization.
