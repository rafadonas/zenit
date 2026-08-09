# ADR-0010: Prepared inspection-order foundation

- Status: accepted
- Date: 2026-08-09

## Context

Sprint 4 requires an inspection order and planned points after the manager's
decision. The currently persisted validation result is based on an estimated
road axis and a prepared zone that are explicitly ineligible for operations.
Treating a review or a generated point as field authorization would violate the
data-quality gates and silently cross the boundary established by ADR-0008.

## Decision

Introduce an immutable prepared inspection-order foundation. An order must
reference the effective, versioned recommendation-review event. The effective
action must be `inspect`: an accepted review inherits the analysis
recommendation, while an adjusted review uses its explicit replacement. A
rejected or superseded review cannot create an order.

Create orders only through an authenticated, idempotent API operation. Derive
the creator from the bearer token and require a non-simulated manager or
supervisor assignment for the target road. Repeat these checks in PostgreSQL so
a direct insert cannot bypass the domain boundary.

Version the provisional policy as `prepared-inspection-order-v1`. It is a
tracked project placeholder, not an official Motiva policy. It creates exactly
three planned points at one-sixth, one-half, and five-sixths of the source
100 m segment centerline. These fractions and the policy provenance are stored
in the database. The point geometry preserves SRID 31983 internally and is
returned as EPSG:4326 with explicit source-data labels.

Fix every order and point in this increment to prepared/non-operational state:
`authorizes_field_work=false`, `eligible_for_field_execution=false`, and
`eligible_for_official_reporting=false`. Protect policies, orders, and planned
points against update/delete; future state changes must be versioned events.

Expose authenticated `POST /v1/work-orders` and `GET /v1/work-orders`. The
public recommendation queue may expose the opaque prepared-order identifier,
but never creator identity. Dashboard creation uses the existing server-held
session, exact-origin validation, CSRF protection, and an allowlisted payload.

## Consequences

- No order exists without an exact analysis, review, segment zone, policy,
  authenticated actor, rationale, and three planned points.
- Centerline fractions are planning placeholders, not surveyed locations. The
  zone and actual GPS point remain field evidence to be captured in Sprint 5.
- A corrected review can produce a new prepared order; the previous order stays
  immutable and non-executable as audit history.
- This increment does not create mowing orders, assign teams, authorize travel
  or field work, implement order events, or start the mobile workflow.
- Operational authorization remains blocked until official/validated geometry
  and a separately approved execution policy exist.
