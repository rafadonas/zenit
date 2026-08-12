# ADR-0045: Simulated mowing post-service summary

- Status: accepted
- Date: 2026-08-12

## Decision

Create a separate versioned, immutable, idempotent summary for a prepared
mowing order. It is generated only after exactly three simulated post-service
measurements and three effective accepted photo reviews (accepted quality and
visible ruler) exist for the same order.

The summary derives minimum, maximum, mean, and N1/N2/N3 counts from typed
post-service measurements only. Photos gate completeness but never supply or
validate numeric height. Keep `post_service`,
`mowing_demo_post_service_only`, `not_collected`, and `simulated` labels, and
keep field evidence, execution, training, official reporting, and field
authorization false.

Dashboard aggregation, exception workflows, map/history updates, and official
reporting remain separate increments.
