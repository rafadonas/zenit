# ADR-0046: Read-only simulated mowing post-service summary dashboard

- Status: accepted
- Date: 2026-08-13

## Decision

Expose generated simulated mowing post-service summaries in the authenticated
dashboard as a read-only aggregation. The dashboard accepts only the existing
non-operational summary contract: three typed measurements, three accepted
visual photo reviews, `post_service`, `mowing_demo_post_service_only`,
`not_collected`, `simulated`, and all field execution, model training, official
reporting, and authorization flags false.

The page does not create map updates, historical vegetation classes, official
reports, or mowing completion claims. It only helps managers inspect the
simulated rehearsal result already persisted by the API.
