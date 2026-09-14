# ADR-0069: Mobile field design tokens and accessible components

- Status: accepted
- Date: 2026-09-14

## Context

Following the stabilization of the ZENIT master design system tokens (`WEB-001`)
and the decomposition of the mobile application architecture (`MOB-001`), the
mobile field application required a cohesive set of design tokens and presentation
primitives (`MOB-002`).

Field mobile operations present distinct physical and environmental constraints:
- direct sunlight and glare that wash out low-contrast UI elements;
- physical operation on uneven roadside terrain requiring generous touch targets;
- critical safety requirements where color must never be the sole conveyor of
  operational status; and
- accessibility needs including screen reader support (`Semantics`) and system font
  scaling (`TextScaler`).

## Decision

1. Align mobile design tokens (`FieldTokens`) directly with the master design system
   (`WEB-001/tokens.css`):
   - brand palette: `#5a26ff` (brand600), `#35129a` (brand800), `#eee9ff` (brand100);
   - canvas, surface, ink, and border tokens;
   - status colors: normal (`#148a45`), attention (`#d8a900`), near-limit (`#f06a32`),
     critical (`#d82c55`), unknown (`#68686f`);
   - historical vegetation height thresholds: N1 `< 10 cm` (`#35a566`),
     N2 `10-30 cm` (`#f1b82d`), and N3 `> 30 cm` (`#e45745`);
   - standard 4-based spacing scale (`space1` through `space12`) and radii.

2. Enforce a minimum touch target of 44x44 px across all interactive field
   components (`FieldButton`, `FieldIconButton`, `FieldTextField`, `FieldStepper`,
   `FieldCard`), satisfying WCAG 2.5.5 / 2.5.8 requirements.

3. Enforce multi-modal status indication ("nenhuma cor como único sinal"):
   - `FieldStatusBadge` always combines an explicit icon, a text label, and
     accessibility semantics;
   - `FieldBanner` always combines a prominent icon, category title, and message;
   - `FieldStepper` combines step numbering, state icons (check mark for complete),
     and textual progress indicators.

4. Enhance outdoor sunlight contrast with crisp borders (`borderStrong`, 1.2–1.5 px)
   and high-contrast text pairings that remain legible in bright daylight.

5. Support dynamic font scaling (`TextScaler`) across all field primitives without
   layout clipping or overflow.

6. Implement `FieldOfflineIndicator` and `FieldTheme` using Flutter standard widgets
   without adding external dependencies.

7. Preserve all non-operational safety disclaimers, simulated rehearsal labels, and
   encrypted local vault protections.

## Consequences

- Mobile UI aligns with the web design system while providing field-hardened ergonomics.
- High outdoor contrast and 44 px touch targets improve legibility and touch accuracy.
- Users with visual or motor impairments receive accessible semantics and scalable text.
- Operational status is never ambiguous because color is always accompanied by icons
  and text.
- Zero external dependencies introduced.
- Prepared and simulated data remains strictly guarded and non-operational.
