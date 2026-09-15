# ADR-0072: Vegetation cover taxonomy proposal

- Status: proposed, pending specialist and data-owner review
- Date: 2026-09-14

## Context

The dashboard and field workflow need a shared vocabulary for the kind of
vegetation that an observation may show. Historical height classes and
operational status already have separate meanings. NDVI and imagery quality do
not support silently inferring height or a mowing decision.

## Proposal

Adopt, for review only, the candidate values `unknown`, `grass_herbaceous`,
`shrub`, `tree`, `mixed`, and `non_vegetation`. Keep coverage, visibility,
occlusion, dominance, spatial relation, quality, rationale, source, and date as
separate attributes. Evaluate left, right, median, and special zones separately.

Use `unknown` for insufficient or conflicting evidence. Preserve a `mixed`
label when relevant types coexist without a defensible dominant object. Record a
tree-crown overhang separately from the trunk's zone. Never derive N1/N2/N3,
height in centimetres, operational status, or field authorization from this
taxonomy.

The complete annotation definitions, edge cases, review flow, and promotion gate
are maintained in [`vegetation-cover-taxonomy-proposal.md`](../data-quality/vegetation-cover-taxonomy-proposal.md).

## Gate

This ADR remains proposed until a vegetation specialist and the data owner
approve the taxonomy, examples, privacy/licence conditions, retention, and a
versioned annotation guide. No official schema, dataset, model training, or
operational report may depend on it before that gate.

## Consequences

- Manual annotation can use stable candidate identifiers without conflating
  coverage with historical height or urgency.
- Ambiguous observations remain visible and route naturally to review.
- Future contract work must cite the approved taxonomy version instead of this
  draft and must preserve source/date/provenance.
- No runtime behavior changes in this proposal; it is a reviewable design
  artifact only.
