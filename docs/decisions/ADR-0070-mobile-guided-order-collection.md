# ADR-0070: Guided mobile order collection journey

- Status: accepted
- Date: 2026-09-14

## Context

The prepared inspection flow already persisted its lifecycle, three height
drafts, photo manifests, and upload receipts in the encrypted mobile vault.
However, the screen exposed the controls as a long technical form. A field user
could not immediately distinguish the next valid action, what existed only on
the device, or what the server had acknowledged. Closing and reopening retained
the data but did not make that continuity evident.

MOB-003 requires an inbox-to-submission journey while retaining the current
prepared/simulated safety boundary. MOB-002 supplies the accessible field
tokens and primitives used by this presentation change.

## Decision

1. Present every prepared order as a semantic field card in the inbox, with an
   explicit local-draft label and the existing non-operational warning.
2. Derive a single next-action message from persisted lifecycle, measurement,
   photo, acknowledgement, and upload state. The message never creates new
   domain state or bypasses controller guards.
3. Show confirmation, simulated start, and finalization in a textual/iconic
   stepper. Color is supplementary and never the only state signal.
4. Group each of the three planned points in its own card with estimated
   location, height, historical N1/N2/N3 class, vault/sync status, photo state,
   and truncated SHA-256 evidence.
5. After finalization, show separate local and sent totals before offering the
   existing manifest sync and explicit photo-byte upload actions.
6. Continue to reload the journey exclusively from the encrypted vault so that
   closing and reopening the screen cannot discard a saved draft.
7. Keep all location, measurement, and photo language explicitly prepared,
   estimated, simulated, or unverified. The journey remains ineligible for
   field authorization, model training, and official reporting.

## Consequences

- The user can identify the next valid step and the local-versus-remote state
  without interpreting raw event lists.
- Existing controller, vault, idempotency, provenance, and API contracts remain
  unchanged.
- The responsive point header wraps at compact widths and is covered at
  `390 x 844` with 200% text scaling.
- Widget coverage executes the full journey, verifies persistence after reopen,
  and checks acknowledged drafts plus uploaded unverified photos.
- No production dependency is added.
