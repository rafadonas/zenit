# WEB-006 corridor map v2

Status: completed locally on branch `feature/web-006-corridor-map-v2`.

## Scope

- Added corridor search parsing for road code, candidate km, and segment index.
- Added class filter for historical vegetation polygons.
- Added an equivalent keyboard-accessible segment list synchronized with map
  selection.
- Kept the detail panel synchronized with map/list/search selection.
- Kept N1/N2/N3 labels tied to the historical 2025-03-28 reference date.
- Updated the map tile failure copy to keep users on the list, filters, and
  details instead of blocking the workflow.
- Added tests for search parsing, 650 segment projection, and corridor/map
  interaction contracts.

## Dependency Note

Vegetation type filtering remains out of scope until `GEO-003` provides the
vegetation-type contract. This ticket only filters the preserved historical
height classes.

## Validation

- `npm run dashboard:lint`
- `npm run dashboard:typecheck`
- `npm run dashboard:test`
- `npm run dashboard:build`
- `npm run dashboard:test -- corridor-dashboard.test.ts segments.test.ts`
