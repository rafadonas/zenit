# ADR-0084: Licence register and privacy baseline as explicit gates

- Status: accepted as a documentation baseline; every entry inside remains unapproved
- Date: 2026-09-15
- Related: ADR-0078, ADR-0073, SEC-001 threat model

## Context

Licence and privacy obligations were scattered across ADRs, the threat model and
the ground truth protocol. Nothing listed, in one place, which external source
may be used for what, which personal data the platform expects to handle, and
who must approve each item. A ticket could therefore ship a capability whose
legal or privacy condition nobody had recorded.

## Decision

Add two baselines under `docs/governance/`:

- `licence-register.md` lists every external and derived source with the intended
  use, the forbidden use, the retention and an approval status. A row that is not
  `approved` blocks the corresponding use even when the code exists.
- `privacy-baseline.md` lists the expected personal data, the pending decisions
  (controller, data protection officer, legal basis, retention, consent, EXIF,
  third parties in photos, viewer IP, international transfer, incidents, impact
  report) and the blocks already in force.

Neither document approves anything: they are the place where a human approval is
recorded, with responsible person, date and signed reference.

PLANET-006 depends on rows L3 and L6 of the register and on decision D6 of the
privacy baseline. Until those are approved, a tile proxy may exist in code only
while disabled by default.

## Consequences

- A blocked capability now has a named owner and a visible reason.
- Approving becomes an explicit act with an audit trail, instead of an
  assumption inside a pull request.
- The baselines do not replace a contract, a provider term of use or legal
  advice, and no academic assumption may override them.
