# WEB-007 recommendations and approval

Status: completed locally on branch `feature/web-007-recommendation-approval`.

## Scope

- Added server-rendered unified queue filters for review state, recommendation,
  and confidence band.
- Added an evidence panel on each recommendation card with acquisition, rule,
  processor, zone data status, and official-report eligibility.
- Clarified confidence as a quality band, not vegetation height.
- Made human review rationale required.
- Added an explicit confirmation checkbox stating that the decision does not
  authorize mowing or field execution.
- Reused existing role checks before rendering review and inspection-order
  actions.
- Added presenter helpers for filtering and effective reviewed recommendation.

## Safety Notes

- `authorizes_field_work` remains required to be `false` by the queue contract.
- Preparing an inspection order is still only available after a reviewed
  inspection decision and remains labeled as non-operational.
- Conflict, missing, invalid, forbidden, and service-unavailable messages remain
  routed through the existing operation-message handling.

## Validation

- `npm run dashboard:lint`
- `npm run dashboard:typecheck`
- `npm run dashboard:test`
- `npm run dashboard:build`
- `npm run dashboard:test -- recommendations.test.ts recommendations-page.test.ts`
