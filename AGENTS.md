# ZENIT - Instructions for Codex

## Read first

Before significant work, read:

1. `docs/manual/README.md` and the chapters it routes for the task
2. `README.md`
3. Relevant files in `docs/decisions/` and `docs/data-quality/`

`ZENIT_Manual_Mestre_para_Codex.pdf` is the immutable version 1.0 source. Use the
maintained Markdown manual for current behavior and the PDF only for historical
verification.

For team-distributed work, also read `docs/team/README.md` and the complete work
package assigned in `docs/team/work-packages.md` before editing code.

When a contributor identifies as Rafael, Guilherme, Lucas, or Gabriel, read
`docs/team/team-assignments.md`, continue that person's existing branch/PR first,
and otherwise select only the first eligible package in that person's queue.

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

## Branch naming

- Use `feature/<ticket>-<slug>` for features and cohesive refactors.
- Use `fix/<ticket>-<slug>` for bug fixes and regressions.
- Use `docs/<ticket>-<slug>` for documentation-only changes.
- Keep branch names lowercase, hyphenated, and limited to one cohesive task.

## Work protocol

1. Inspect instructions, repository state, and task scope.
2. Define a small plan, affected files, and expected tests.
3. Ask before architectural, destructive, network, or dependency changes.
4. Implement cohesive changes and run relevant checks.
5. Review scope, security, provenance, and simulation labels.
6. Update documentation, ADRs, and contracts when behavior changes.
7. Commit every completed repository change before reporting it; never leave
   completed work uncommitted. Keep each commit cohesive. For team-distributed
   work, push the validated ticket branch and hand it off through a pull request;
   never push directly to `main`.
8. Report changes, tests, limitations, and the recommended next step.

## Forbidden without explicit request

- Direct push to `main`, force push, history rewrite, hard reset, or branch deletion.
- Disabling sandbox or approvals.
- Reading or printing secrets.
- Replacing raw data, deleting evidence, or automatically promoting a model.
- Treating model confidence as an exact probability of vegetation height.
