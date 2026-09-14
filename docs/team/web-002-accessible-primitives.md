# WEB-002 accessible primitives

Status: completed locally on branch `feature/web-002-accessible-primitives`.

## Scope

Implemented the first dashboard primitive layer without adding dependencies:

- `Button` and `IconButton`;
- `Badge` and `DataStatus`;
- `Alert`;
- `Card`;
- `EmptyState`, `ErrorState`, and `Skeleton`;
- `Field` and `Select`;
- `Tabs`;
- `Dialog` and `Drawer`.

Exports are available from `apps/dashboard/src/components/ui`.

## API Notes

- `Button` supports `variant`, `size`, `loading`, `loadingLabel`, `disabled`,
  optional icon placement, and defaults `type` to `button`.
- `IconButton` requires an `aria-label` in the TypeScript props and supports
  loading/disabled states.
- `DataStatus` exposes real, estimated, simulated, prepared, and inconclusive
  labels using non-color text.
- `Alert` defaults to `role="status"` and uses `role="alert"` for critical tone.
- `Field` links labels with native controls and propagates hint/error IDs through
  `aria-describedby`; errors set `aria-invalid`.
- `Tabs` emits native buttons or links with `role="tablist"` and `role="tab"`.
- `Dialog` and `Drawer` use native `<dialog>` markup and include a close control
  through `method="dialog"`.

## Accessibility Contract

- Interactive targets use 44 px minimum dimensions except compact `Button size="sm"`,
  which is reserved for dense secondary contexts.
- Hover, focus, disabled, loading, and reduced-motion styles are in
  `apps/dashboard/src/styles/primitives.css`.
- Keyboard focus continues to come from the shared focus token in
  `apps/dashboard/src/styles/base.css`.

## Validation

- `npm run dashboard:lint`
- `npm run dashboard:typecheck`
- `npm run dashboard:test`
- `npm run dashboard:build`
- `npm run dashboard:test -- primitives.test.ts`
