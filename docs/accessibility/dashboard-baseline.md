# Dashboard accessibility baseline

- Assessment date: 2026-08-14
- Scope: P0 evaluation dashboard
- Status: automated baseline, not a WCAG conformance claim

## Enforced checks

- The root layout provides a keyboard-visible skip link to `#main-content`.
- Every current dashboard `<main>` shell provides exactly one shared skip
  target.
- Links, buttons, form controls, summaries, and button-role map segments receive
  an explicit visible focus treatment.
- The loading animation and transitions respect `prefers-reduced-motion`.
- The normal muted-text token maintains at least a 4.5:1 contrast ratio on the
  primary page and card surfaces.
- Next.js core-web-vitals lint continues to apply JSX accessibility rules.

The Vitest contract discovers TSX files containing `<main>`, so a new shell
without the shared target fails the dashboard test suite. It also calculates
the contrast ratio directly from the CSS color tokens.

## Remaining manual validation

- Complete keyboard traversal and focus order in supported browsers.
- Screen-reader behavior for dynamic status messages, long review forms, and
  the interactive SVG corridor map.
- Reflow at 200% and 400% zoom across desktop and mobile widths.
- Contrast review for every state-specific hardcoded color and image content.
- Touch target sizing and behavior on representative field devices.

These checks must be completed before any operational deployment. The current
baseline does not change the prepared/simulated status of data or authorize
field work.
