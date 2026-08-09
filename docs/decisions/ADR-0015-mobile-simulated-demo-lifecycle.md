# ADR-0015: Mobile simulated demo lifecycle

- Status: accepted
- Date: 2026-08-09

## Context

ADR-0014 introduced the server boundary for a simulated prepared-order
lifecycle. The Flutter app still synchronized only three measurements and
could not demonstrate confirmation, start, and finish while offline.

## Decision

Persist three lifecycle events in the encrypted user-bound vault. Require the
local sequence confirmation, start, three prepared measurements, then finish.
Use the first estimated planned point as a demo coordinate only, labeling it
`simulated`, `demo_only`, and `prepared_point_demo_v1` in storage, payload, and
UI. Do not access a device location service in this increment.

Create persistent UUIDs before network use. On finish, atomically prepare one
ordered batch containing confirmation, start, three measurements, and finish.
Retry the exact same six event IDs and batch ID. Retain persistent outcomes for
both lifecycle and measurement events, including rejection and conflict.

## Consequences

- The full Sprint 5 lifecycle can be demonstrated with the network disabled.
- The UI visibly distinguishes the environment and simulated coordinate.
- Neither the app nor server mutates the immutable prepared order.
- Photos, real GPS, device tracking, geofence validation, and official field
  completion remain unavailable.
