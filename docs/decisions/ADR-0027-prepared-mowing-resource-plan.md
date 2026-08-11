# ADR-0027: Prepared mowing resource plan

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0026 creates a non-executable mowing-order foundation but leaves team and
equipment unassigned. No official team or equipment catalog, identifier, or
availability source is present in the repository. Inventing those values would
misrepresent project placeholders as Motiva operational data.

## Decision

Record candidate team and equipment references as immutable, idempotent
prepared resource-plan events. Both references are manually supplied text,
limited in length, and always labelled
`prepared_placeholder_pending_validation`. They are not verified assignments.

Allow an active manager or supervisor for the road to create the first plan or
append a correction that supersedes the one effective plan. Serialize the
linear chain per mowing order. Also acquire the proposal-review lock before the
resource-plan lock so a review correction cannot race resource planning for an
obsolete mowing order. Repeat current-source, policy, role, chain, and safety
checks in PostgreSQL.

Keep team and equipment assignment states `unassigned`. Every plan still
requires operational approval, is ineligible for field execution and official
reporting, and cannot authorize work.

## Consequences

- Planning can name resource candidates without claiming availability or an
  official catalog match.
- Corrections preserve the complete history and one unambiguous effective plan.
- A superseded proposal review blocks new planning against the obsolete order.
- Verified catalogs, availability, actual assignment, scheduling, weather,
  safety clearance, and operational approval remain future increments.
