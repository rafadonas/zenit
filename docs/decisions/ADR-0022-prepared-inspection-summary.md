# ADR-0022: Prepared inspection summary

- Status: accepted
- Date: 2026-08-11

## Context

The prepared mobile lifecycle can return three typed measurements and three
uploaded photos, while ADR-0021 records human image-quality and ruler-visibility
reviews. The loop still lacked a provenance-safe derived result. Producing an
ordinary operational report would falsely present simulated location and
prepared demo inputs as field execution.

## Decision

Create a versioned prepared-summary policy and an immutable, idempotent summary
per inspection order. Generation requires a persisted simulated finish, exactly
three distinct planned-point measurements, and three uploaded photos whose
latest effective human reviews are accepted with accepted quality and visible
rulers. Require a current non-simulated manager or supervisor role on the road.

Calculate minimum, maximum, mean, and historical class counts from the typed
measurements only: N1 below 10 cm, N2 from 10 through 30 cm, and N3 above 30 cm.
PostgreSQL recomputes the aggregates and evidence gates before insert.

Fix every summary to simulated location, prepared reviewed non-operational
evidence, and ineligible for field evidence, model training, official reporting,
or field authorization. Photo pixels are never converted into height.

## Consequences

- The prepared input-to-feedback loop gains a reproducible derived result.
- Idempotency and one-summary-per-order constraints prevent duplicate reports.
- An accepted photo review supports completeness only; it does not validate the
  typed numeric measurement or promote real field evidence.
- Operational GPS, validated measurements, official report templates, retention,
  and any mowing proposal after inspection remain separate increments.
