# WEB-005 decision-oriented overview

Status: completed locally on branch `feature/web-005-decision-overview`.

## Scope

- Reworked the overview hierarchy around situation, attention, and next action.
- Added per-metric data status, source, and visible temporal reference.
- Added partial error handling inside the overview so unavailable upstream data is
  not converted into assumed KPIs.
- Added empty state for queues without a next decision item.
- Added stale temporal reference labeling when the latest acquisition is older
  than 30 days or absent.
- Added role-based shortcuts for manager, supervisor, and public contexts.

## Safety Notes

- No fictitious KPI values are introduced; values render only from loaded segment
  and recommendation API payloads, or as zero when that payload is unavailable and
  explicitly marked by an error state.
- Prepared and estimated data remain visibly labeled.
- The overview continues to state that no dashboard action authorizes field work.

## Validation

- `npm run dashboard:lint`
- `npm run dashboard:typecheck`
- `npm run dashboard:test`
- `npm run dashboard:build`
- `npm run dashboard:test -- overview.test.ts accessibility-contract.test.ts`
