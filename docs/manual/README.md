# ZENIT master manual

- Version: 2.0
- Updated: 2026-09-13
- Status: living project specification for the academic P0 demonstration

This directory is the maintained Markdown edition of the original 44-page
`ZENIT_Manual_Mestre_para_Codex.pdf` (version 1.0, 2026-08-06). It preserves the
product and domain intent while reconciling the proposed architecture and backlog
with the implementation that now exists in the repository.

The source PDF remains an immutable historical input. Its SHA-256 is
`a8d2613c9c57dad5703522ceec871d15b6ec18a5fe16c8354ff31fc5e798c5e2`.
When this edition and the PDF differ about current software behavior, accepted
ADRs, versioned contracts, migrations, tests, and the current repository take
precedence. Source or contractual claims retain their source status and are not
silently rewritten as project decisions.

## Reading order

1. [Product, domain and evidence](product-domain-and-evidence.md)
2. [Architecture, data and security](architecture-data-and-security.md)
3. [Delivery, validation and governance](delivery-validation-and-governance.md)
4. [PDF source companions](../reference/README.md)
5. [Accepted architecture decisions](../decisions/)

## Current product boundary

ZENIT is a road-vegetation monitoring platform connecting road geometry,
satellite evidence, explainable recommendations, human review, prepared field
workflows, photos, typed measurements, and reporting. The implemented repository
is a reliable **local academic demonstration**, not a production or operational
system.

The end-to-end intent remains:

```text
road and source data
  -> geospatial segmentation and evidence quality
  -> explainable recommendation
  -> explicit human review
  -> prepared inspection or mowing plan
  -> offline-capable mobile capture and synchronization
  -> reviewed evidence, history and reporting
```

No AI result, confidence value, prepared order, or simulated rehearsal authorizes
mowing. Current field and mowing flows deliberately preserve false eligibility
flags and explicit prepared/simulated labels.

## Non-negotiable domain rules

- analyze 100 m road segments;
- keep left, right, median, and special zones separate;
- use 30 cm as the general vegetation-height threshold;
- use 10 cm in special and operational areas;
- preserve historical classes N1 `< 10 cm`, N2 `10-30 cm`, and N3 `> 30 cm`;
- normally route low-confidence evidence to inspection;
- preserve human decisions, audit history, source lineage, and rule/model versions;
- never train on or officially report demo, prepared, or simulated data; and
- label the spreadsheet reference date as 2025-03-28, never as current condition.

## Authority order

Use the following order when sources conflict:

1. applicable law, contract, concession document, and formally adopted policy;
2. source challenge requirements;
3. supplied source data with its date, checksum, and quality limitations;
4. accepted ADRs and versioned contracts;
5. this maintained manual and repository instructions;
6. configurable demonstration assumptions; and
7. explicit, reviewable inference.

For this academic project, Rafael may record product-scope decisions. That does
not convert academic judgment into legal, contractual, privacy, operational, or
professional certification. External source licenses and limitations still apply.

## Status vocabulary

| Label | Meaning | Required treatment |
| --- | --- | --- |
| source | Directly supported by an identified source | Preserve citation and context. |
| decision | Adopted project choice | Change through a reviewed ADR when architectural. |
| real | Captured from a real provider or observation | Still requires quality and provenance checks. |
| estimated | Derived by a method or model | Show method, time, uncertainty, and limitations. |
| prepared | Structurally realistic but non-operational | Never present as executed or authorized. |
| simulated | Created only for demonstration or rehearsal | Exclude from training and official reports. |
| inconclusive | Evidence cannot support a conclusion | Preserve uncertainty and normally request inspection. |
| future | Planned but not implemented | Do not describe as available. |
| blocked | Missing approval, evidence, predecessor, or operational policy | Do not bypass the gate. |

## What changed from version 1.0

- replaces the proposed monorepo description with the implemented FastAPI,
  PostGIS, Next.js, Flutter, MinIO, Docker Compose, contracts, and worker layout;
- records the prepared/simulated workflow and its safety gates;
- reflects provider-neutral Sentinel, CBERS, and discovery-only Planet support;
- links the versioned OpenAPI contract and 67 accepted ADRs instead of listing a
  speculative endpoint set;
- replaces the original sprint backlog with the current four-person work packages;
- incorporates the QA-001 E2E baseline, SEC-001 threat model, and API-001 queue
  analysis; and
- moves source-specific material into traceable Markdown companions instead of
  treating every PDF statement as current implementation.

## Source-to-Markdown map

| Original manual chapters | Maintained destination |
| --- | --- |
| 1-8: product, sources, domain, flows and AI | [Product, domain and evidence](product-domain-and-evidence.md) |
| 9-13: architecture, data, APIs, security and repository | [Architecture, data and security](architecture-data-and-security.md) |
| 14-21: priorities, roadmap, tests, pilot, demo, assumptions and DoD | [Delivery, validation and governance](delivery-validation-and-governance.md) |
| Appendices A-D: agent/configuration/prompts | [`AGENTS.md`](../../AGENTS.md) and [team delivery hub](../team/README.md) |
| Appendices E-F: glossary and references | This index and [PDF source companions](../reference/README.md) |
