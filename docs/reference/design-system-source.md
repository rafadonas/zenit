# ZENIT design-system PDF companion

- Source: `ZENIT_Design_System_Motiva.pdf`, version 1.0, August 2026, 28 pages
- SHA-256: `cb0c6729d95b0cb2e7379664de070c43707787a10597ea3916310bd2ddd112cf`

This companion makes the visual source searchable while separating its conceptual
mock data from current product behavior. The maintained implementation specification
is [`docs/team/design-system.md`](../team/design-system.md). If they differ, the
maintained specification, accessibility baseline, and implemented tokens/components
take precedence.

The PDF says it is inspired by Motiva's visual universe but does not reproduce or
authorize official Motiva brand assets. That limitation remains in force.

## Direction

The experience should turn analysis into a calm, human-readable decision flow. Four
source principles guide it:

1. movement with purpose;
2. data before ornament;
3. operational calm; and
4. human and trustworthy interaction.

The source promises that a user should understand the risk, reason, and next action
within roughly ten seconds. This is a usability target, not a measured SLA.

The recommended visual balance is approximately 70% light base, 20% identity, and
10% data/status color. Curves and motion should guide attention rather than decorate
the interface.

## Visual foundation

### Source palette

| Role | Source value | Maintained interpretation |
| --- | --- | --- |
| ZENIT indigo | `#5A26FF` | navigation, selection, focus, primary action |
| dark indigo | `#35129A` | hover/pressed and dark surfaces |
| lilac | `#EEE9FF` | quiet selected/highlight background |
| canvas | `#F7F7FA` | application background |
| surface | `#FFFFFF` | cards, drawers, dialogs |
| text | `#202024` | primary content |
| secondary text | `#68686F` | metadata after contrast validation |
| border | `#E4E3EC` | separators and control borders |
| normal | `#148A45` | operational normal with icon and label |
| attention | `#D8A900` | attention with icon and label |
| near limit | `#F06A32` | proximity to threshold with icon and label |
| critical | `#D82C55` | critical state with icon and label |

Color never carries status alone. Indigo is not a severity color, and green is not a
generic success claim.

### Type, spacing, and shape

- Inter is a candidate only when packaged/licensed; use a system fallback otherwise.
- Default body is 16/24; operational minimum is 14/20.
- Source title scale ranges from 20/28 through 32/40 with weights 400-600.
- Spacing uses a 4 px base and favors 8, 12, 16, 24, 32, 40, and 48.
- Desktop grid uses 12 columns, tablet 8, and mobile 4.
- Controls, cards, and high-emphasis panels use progressively larger radii.
- Focus must remain visible; shadow cannot replace an outline or border.

## Components and states

The PDF covers cards, prioritized lists, tables, status chips, buttons, inputs,
filters, dialogs, drawers, tooltips, loading, empty, error, and success states.
Maintained requirements are:

- one primary action per decision context;
- loading prevents duplicate submission;
- destructive actions use explicit language and proportional confirmation;
- inputs expose labels, instructions, error association, and focus;
- dialogs trap focus, close with Escape when safe, and return focus;
- tooltips never contain essential or interactive-only content;
- empty, stale, forbidden, partial, and dependency-failure states remain distinct;
- tables use captions and announced sorting and transform to accessible mobile views;
  and
- evidence remains readable even when image bytes or map tiles are unavailable.

The canonical component list and asynchronous state vocabulary are in the
[executable design system](../team/design-system.md).

## Semantic separation

The source PDF visually demonstrates operational status. The maintained system adds a
strict separation among:

- operational urgency: normal, attention, near limit, critical;
- historical height class: N1, N2, N3;
- vegetation cover type: unknown, grass/herbaceous, shrub, tree, mixed,
  non-vegetation; and
- evidence status: real, estimated, prepared, simulated, inconclusive.

These dimensions must not reuse the same label or color legend. For example, a tree
may be normal and grass may be critical; neither type proves height.

## Map and visualization

The map is a primary exploration surface, never the only accessible representation.
It requires:

- visible attribution and provider/source date;
- restrained basemap styling and legible labels;
- independent hover, focus, selection, and severity styles;
- persistent legend and active-filter context;
- list/table equivalence synchronized with selection;
- readable operation when external tiles fail;
- short tooltip plus complete drawer/detail view; and
- no implication that a displayed polygon is current, official, or measured unless
  its metadata supports that claim.

Charts need titles, units, time periods, textual summaries, accessible values, and
honest empty/partial states. Do not use smoothing or decorative animation to imply
precision that the source does not contain.

## Responsive behavior

| Source range | Maintained behavior |
| --- | --- |
| 1280 px and wider | Expanded navigation and side-by-side operational context where useful. |
| 768-1279 px | Compact navigation and progressive disclosure. |
| below 768 px | Single-column flow, drawer/bottom-sheet context, touch targets at least 44 px. |

The maintained regression widths are 360, 768, 1024, 1280, and 1440 px plus 200%
zoom. Reflow is more important than matching the static mockup.

## Accessibility

The source calls for contrast, keyboard operation, semantic structure, touch targets,
focus, reduced motion, and alternatives to visual-only information. Current work uses
WCAG 2.2 AA as its design target without claiming formal conformance.

Motion durations in the source range from approximately 120 ms for microfeedback to
300 ms for rare transitions. `prefers-reduced-motion` removes non-essential movement.

## Screen concepts

The PDF illustrates login, overview, monitoring map, segment detail, work orders,
weekly planning, and reports. These are direction, not screenshots of implemented
behavior.

- **Login:** clear environment/profile context and concise error behavior.
- **Overview:** situation, attention, and next action before detail.
- **Map:** corridor context, filters, legend, selection, and equivalent list.
- **Segment detail:** evidence, source, date, confidence, limitation, and safe action.
- **Orders/planning:** visually separate recommendation, approval, plan, and execution.
- **Reports:** methodology, period, provenance, and limitations beside metrics.

Values such as `128 km`, `14`, `94%`, `32 cm`, `91%`, work-order identifiers, weekly
counts, and report KPIs are illustrative mock content. They are not Motiva values,
current ZENIT observations, accepted targets, or official report data.

## Page map

| PDF pages | Content |
| ---: | --- |
| 1 | cover, scope, and non-official brand direction |
| 2-4 | experience promise, visual concept, and product principles |
| 5-7 | palette, typography, grid, spacing, elevation |
| 8-12 | shell, cards/lists/tables, status, controls, dialogs and feedback |
| 13-16 | system states, map, charts, responsive behavior |
| 17-18 | accessibility, motion, iconography, photography |
| 19-25 | login, overview, map, segment, orders, planning, and reports |
| 26 | candidate CSS tokens |
| 27 | consistency and governance |
| 28 | references, scope, and suggested rollout |

## Updated governance

The PDF's direction is retained, but brand permission is not assumed. New tokens and
shared components require a cohesive ticket, consumer migration, accessibility
checks, and review by the dashboard/design owner. Screenshots and telemetry require a
separate privacy/tooling decision. Generated or illustrative imagery must be labeled
and may not serve as field evidence or training data.
