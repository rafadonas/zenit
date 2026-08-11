# ADR-0021: Prepared photo human review

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0020 allows authorized users to retrieve exact uploaded photo bytes, but a
visual inspection had no versioned policy or immutable outcome. Treating file
receipt or successful decryption as proof of usable photographic evidence would
collapse transport integrity, image quality, ruler visibility, and operational
validation into one unsafe status.

## Decision

Create a prepared photo-review policy whose allowed roles are configurable and
whose initial values are project placeholders, not official Motiva policy.
Managers and supervisors with a current non-simulated role on the photo's road
may append an idempotent human review.

Provide an authenticated review queue scoped by the same current road roles.
Expose only operational context, safe media metadata, and the latest effective
review; do not expose reviewer identity, device identity, object-store
coordinates, or encryption metadata.

Record decision, image-quality status, ruler-visibility status, rationale,
reviewer identity, policy version, timestamp, and optional supersession. An
accepted decision requires both accepted image quality and a visible ruler.
Rejected and inconclusive decisions require a rationale. Corrections append a
new review that supersedes a review of the same photo.

Fix every outcome, including acceptance, to `prepared` and ineligible for field
evidence, model training, official reporting, and field authorization. A visible
ruler is not a validated height and no numeric measurement is inferred from the
image.

## Consequences

- Human visual outcomes are retry-safe, immutable, attributable, and versioned.
- Review clients can discover eligible photos without possessing raw photo IDs.
- PostgreSQL repeats target, active identity, road role, policy, supersession,
  and non-operational safety checks.
- The review can support later validation work without promoting prepared demo
  data or silently authorizing mowing.
- The dashboard uses same-origin authenticated proxies, CSRF protection, strict
  response contract validation, and no-store image delivery.
- Decoded-image safety checks, EXIF handling, numeric measurement comparison,
  and operational evidence promotion remain separate increments.
