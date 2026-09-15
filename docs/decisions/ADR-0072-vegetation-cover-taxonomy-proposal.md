# ADR-0072: Vegetation cover taxonomy proposal

- Status: proposed, project-owner scope decision recorded; specialist validation
  unavailable
- Date: 2026-09-14

## Context

The dashboard and field workflow need a shared vocabulary for the kind of
vegetation that an observation may show. Historical height classes and
operational status already have separate meanings. NDVI and imagery quality do
not support silently inferring height or a mowing decision.

## Proposal

Adopt, for review only, the candidate values `unknown`, `grass_herbaceous`,
`shrub`, `tree`, `mixed`, and `non_vegetation`. Keep coverage, visibility,
occlusion, dominance, spatial relation, quality, rationale, GPS status, source,
and date as separate attributes. Evaluate left, right, median, and special
zones separately. Allow new values only through a new taxonomy version.

Use `unknown` for insufficient or conflicting evidence and require a controlled
`unknown_reason` such as shadow, blur, canopy occlusion, source conflict, or
insufficient resolution. Preserve a `mixed` label when relevant types coexist
without a defensible dominant object. Record a tree-crown overhang separately
from the trunk's zone. The taxonomy is an input/output label space for an
AI-assisted classifier, but every estimate remains versioned, uncertain, and
subject to human review. Never derive N1/N2/N3, height in centimetres,
operational status, or field authorization from this taxonomy.

The complete annotation definitions, edge cases, review flow, and promotion gate
are maintained in [`vegetation-cover-taxonomy-proposal.md`](../data-quality/vegetation-cover-taxonomy-proposal.md).

## Gate

The project data owner has formally accepted this scope for the demonstration:
the absence of a dedicated specialist is recorded as a limitation, the six base
classes remain extensible by version, and a future AI experiment is in scope.
The ADR remains proposed because no specialist validation has occurred. The
draft may support a versioned, real-data training experiment after the dataset,
licence/consent, and quality gates are complete, but it may not become an
official operational schema or support field authorization. Prepared/simulated
evidence is never eligible for training or official reporting.

## Consequences

- Manual annotation and a future AI classifier can use stable candidate
  identifiers without conflating coverage with historical height or urgency.
- Ambiguous observations remain visible and route naturally to review.
- Future contract work must cite the approved taxonomy version instead of this
  draft and must preserve source/date/provenance.
- No runtime behavior changes in this proposal; it is a reviewable design
  artifact only.
