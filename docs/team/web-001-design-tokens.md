# WEB-001 design token extraction

Status: completed locally on branch `feature/web-001-design-tokens`.

## Scope

- Extracted dashboard global design tokens to `apps/dashboard/src/styles/tokens.css`.
- Extracted global reset, body defaults, keyboard focus, and reduced motion behavior
  to `apps/dashboard/src/styles/base.css`.
- Kept `apps/dashboard/src/app/styles.css` focused on route and component rules.
- Preserved compatibility aliases such as `--ink`, `--muted`, `--paper`,
  `--card`, `--line`, `--green`, `--green-dark`, `--mint`, `--amber`,
  `--amber-soft`, and `--shadow`.
- Added semantic status and historical height-class tokens so critical UI colors
  are not hardcoded in component CSS.

## Token Coverage

Canonical tokens now cover:

- brand colors: `--color-brand-600`, `--color-brand-800`,
  `--color-brand-100`;
- neutral colors: `--color-canvas`, `--color-surface`, `--color-text`,
  `--color-text-muted`, `--color-border`;
- operational status: normal, attention, near limit, critical, and unknown;
- historical height classes: `--color-height-n1`, `--color-height-n2`,
  `--color-height-n3`;
- typography, spacing, radius, shadows, motion, focus, breakpoints, and z-index.

## Contrast Checks

Computed contrast ratios:

| Pair | Ratio |
| --- | ---: |
| `--color-text-muted` on `--color-canvas` | 5.17 |
| `--color-text-muted` on `--color-surface` | 5.53 |
| `--color-brand-600` on `--color-surface` | 6.65 |
| near-limit text on near-limit surface | 6.99 |
| normal text on normal surface | 6.60 |

All listed pairs meet WCAG AA for normal text.

## Validation

- `npm run dashboard:lint`
- `npm run dashboard:typecheck`
- `npm run dashboard:test`
- `npm run dashboard:build`
- `npm run dashboard:test -- accessibility-contract.test.ts`
