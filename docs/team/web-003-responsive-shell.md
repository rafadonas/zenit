# WEB-003 responsive shell

Status: completed locally on branch `feature/web-003-responsive-shell`.

## Scope

- Kept the shared dashboard header as the single shell navigation source.
- Added explicit route context for area, road, or workflow labels.
- Added compact navigation labels for tablet and mobile layouts.
- Added session role context for manager/supervisor road scopes when available.
- Added `tabIndex={-1}` to each `main#main-content` target so navigation and the
  skip link have a stable focus destination.
- Moved mobile navigation to a fixed bottom bar with 44 px targets.

## Access Control Notes

The shell only displays the current authenticated role context. Action visibility
continues to be enforced inside the route flows, where manager/supervisor scope is
checked against each road and simulated roles remain blocked from operational
review actions.

## Validation

- `npm run dashboard:lint`
- `npm run dashboard:typecheck`
- `npm run dashboard:test`
- `npm run dashboard:build`
- `npm run dashboard:test -- dashboard-header.test.ts accessibility-contract.test.ts`
