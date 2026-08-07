# ZENIT - Instructions for Codex

## Read first

Before significant work, read:

1. `ZENIT_Manual_Mestre_para_Codex.pdf`
2. `README.md`
3. Relevant files in `docs/decisions/` and `docs/data-quality/`

## Product goal

Build a road-vegetation monitoring platform connecting satellite data,
geospatial processing, explainable recommendations, human approval, field work,
photos/GPS/measurements, and operational reporting.

## Non-negotiable domain rules

- Analyze 100 m road segments and separate left, right, median, and special zones.
- Use 30 cm as the general threshold and 10 cm for special/operational areas.
- Preserve historical classes: N1 < 10 cm; N2 10-30 cm; N3 > 30 cm.
- Low confidence normally creates an inspection recommendation.
- AI must never silently authorize mowing.
- Preserve human approvals, audit trails, rule/model versions, and provenance.
- Clearly label real, estimated, simulated, prepared, and inconclusive data.
- Never use demo or simulated data for model training or official reports.
- The spreadsheet reference date is 2025-03-28; do not present it as current.

## Data safety

- Never modify files under `data/raw/`.
- Register checksums and lineage for imports and derived products.
- Do not commit source documents, secrets, large imagery, or personal data.
- Normalize `classificacao_rocada.kmz` without changing its original and mark
  inferred attribute mappings as pending validation.

## Scope and engineering

- Work one approved sprint or cohesive task at a time.
- Do not implement P1/P2 features before P0 without explicit approval.
- Do not invent official Motiva values; use configurable, tracked placeholders.
- Use English for code, identifiers, technical filenames, and commits.
- Target FastAPI/Python, PostgreSQL/PostGIS, Next.js/TypeScript, Flutter, and Docker.
- Prefer a modular monorepo over premature microservices.
- Use migrations, type checks, lint, tests, idempotent imports, and explicit SRIDs.
- Ask before adding production dependencies or enabling network access.

## Work protocol

1. Inspect instructions, repository state, and task scope.
2. Define a small plan, affected files, and expected tests.
3. Ask before architectural, destructive, network, or dependency changes.
4. Implement cohesive changes and run relevant checks.
5. Review scope, security, provenance, and simulation labels.
6. Update documentation, ADRs, and contracts when behavior changes.
7. Report changes, tests, limitations, and the recommended next step.

## Forbidden without explicit request

- Push, force push, history rewrite, hard reset, or branch deletion.
- Disabling sandbox or approvals.
- Reading or printing secrets.
- Replacing raw data, deleting evidence, or automatically promoting a model.
- Treating model confidence as an exact probability of vegetation height.
