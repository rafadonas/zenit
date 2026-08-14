# ADR-0054: Dashboard accessibility baseline

- Status: accepted
- Date: 2026-08-14

## Decision

Provide one skip link in the root layout and one `main-content` target in every
dashboard shell. Apply a global visible keyboard-focus treatment, respect the
user's reduced-motion preference, and darken the shared muted-text token until
normal text reaches at least 4.5:1 contrast on the primary page and card
surfaces.

Enforce these invariants with the existing Vitest and Next.js ESLint toolchain.
The test discovers current TSX main shells, verifies the skip target and CSS
contracts, and calculates contrast from the source color tokens without adding
a browser-test dependency.

## Consequences

Keyboard users can bypass repeated navigation, controls have a consistent focus
indicator, reduced-motion users do not receive the loading animation, and the
most reused secondary text color meets the normal-text contrast baseline.

This is not a complete WCAG conformance audit. Browser, zoom, screen-reader,
interactive-map, touch-target, and state-specific color testing remain manual
hardening work before operational use.
