# ADR-0065: Shared navigation and progressive decision disclosure

- Status: accepted
- Date: 2026-09-10

## Context

The dashboard repeated a six-link header on each route and exposed internal
queue names as separate product destinations. Recommendation cards also placed
acquisition metadata, policy and processor versions, identifiers, correction
forms, and the main human decision at the same visual level. The information
was valid but made the demonstration hard to follow.

## Decision

Use one shared dashboard header with five product areas: overview, map,
decisions, field, and results. Existing evidence and post-service routes remain
available; related routes share the same active product area instead of
becoming separate top-level destinations.

Present recommendation cards in three layers:

1. segment, zone, recommendation, confidence, and a short explanation;
2. the pending human decision or the latest recorded decision;
3. correction controls and technical audit metadata inside explicit expandable
   details.

Translate known processor explanations for presentation, while preserving an
unknown reason verbatim so future processor output is not silently discarded.
Keep UUIDs, rule versions, policy versions, processor versions, review counts,
and acquisition timestamps available in the audit layer.

## Consequences

- The primary navigation matches the five-stage demonstration story.
- A reviewer can act without first parsing implementation identifiers.
- Recorded decisions remain easy to understand, while corrections stay
  available and append-only.
- No API contract, role check, CSRF protection, idempotency key, audit field, or
  field-authorization boundary changes.
- The next increment can combine the two photo-review experiences behind the
  shared field destination without breaking their current routes.
