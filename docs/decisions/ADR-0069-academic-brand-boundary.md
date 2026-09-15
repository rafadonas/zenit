# ADR-0069: Academic ZENIT brand boundary

- Status: accepted
- Date: 2026-09-15

## Context

GOV-002 required a decision about use of Motiva name, logo, colors, and branded
assets before the dashboard design system could be treated as more than a visual
direction. The repository is an academic project built for a college
demonstration. The team does not have a direct relationship, sponsorship,
authorization, or brand license from Motiva.

The source challenge and design PDFs remain useful context, but their references
to Motiva do not grant permission to reproduce corporate identity, imply
endorsement, or present ZENIT as a Motiva product.

## Decision

Treat ZENIT as its own academic project brand. The dashboard, mobile app, docs,
and generated artifacts may use the ZENIT name, project-specific copy, and the
current ZENIT token palette as demonstrative product identity.

Do not use Motiva logos, proprietary brand assets, official typography, official
color systems, slogans, endorsement language, or layouts that imply the project
is operated, sponsored, certified, or approved by Motiva.

Motiva may be mentioned only as source/challenge context, source-file naming, or
background reference when that context is already present in supplied materials.
Such mentions must not be used as a product brand, customer claim, operational
authority, or permission statement.

Keep the current dashboard token values as ZENIT academic placeholders. They are
not Motiva brand colors or operational policy values. A future official or
partnered use must replace this assumption with reviewed written permission,
usage limits, and updated tokens/assets.

## Consequences

- GOV-002 is unblocked for the academic demonstration and design-system
  governance.
- The UI can continue using a ZENIT-only identity without waiting for official
  Motiva brand approval.
- Any official Motiva logo, official palette, customer-facing endorsement,
  production marketing page, or deployment that suggests affiliation remains
  blocked until explicitly authorized.
- This decision does not grant legal, privacy, operational, regulatory, field,
  reporting, or data-owner authority.
- WEB-010 remains blocked because screenshot monitoring, telemetry, privacy, and
  external tooling still require a separate decision.
