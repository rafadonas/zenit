# WEB-009 results and history

Status: completed locally on branch `feature/web-009-results-history`.

## Scope

- Added a post-service result-history presenter.
- Added a visible before/after/comparison block to each result card.
- Explicitly blocks before-after deltas when the current contract has no
  compatible before measurement with source and date.
- Kept simulated post-service source/date separate from unavailable before data.
- Clarified export copy so CSV generation preserves status/provenance and remains
  blocked for official reporting, training, and field authorization.

## Safety Notes

- Results remain `simulated_reviewed_non_operational`.
- No before value is invented.
- No simulated result is promoted to field evidence, field execution, model
  training, or official reporting.

## Validation

- `npm run dashboard:lint`
- `npm run dashboard:typecheck`
- `npm run dashboard:test`
- `npm run dashboard:build`
- `npm run dashboard:test -- mowing-post-service-summaries.test.ts mowing-post-service-results-page.test.ts mowing-post-service-operation-message.test.ts`
