# ADR-0064: Simplified demonstration entry point

- Status: accepted
- Date: 2026-09-09

## Context

The manager dashboard opened directly on the recommendation queue. That screen
combines review controls, internal policy metadata, audit identifiers, prepared
order state, and repeated safety language. It validates the implementation but
does not explain the product clearly to a first-time evaluator.

The local fixed-session redirect also made the running-stack smoke verifier
fail because its HTTP client did not retain the cookie issued during the
redirect chain.

## Decision

Add `/overview` as the manager demonstration entry point. Present the P0 story
as five stages: monitor, analyze, decide, inspect, and conclude. Show only live
counts derived from the existing segment and recommendation APIs, one next
decision, and a concise statement of what the demonstration does and does not
prove.

Keep every existing route and authorization check. The overview is read-only
and cannot create a review or work order. Change the fixed manager home path to
`/overview`; the supervisor continues to open the post-service evidence queue.

Make the stack smoke client retain HTTP cookies and verify the rendered
overview after the fixed-session redirect. Login rendering remains covered by
the dashboard route tests rather than the fixed-session stack smoke.

## Consequences

- A first-time viewer sees the product flow before implementation detail.
- Existing engineering and audit screens remain reachable for deeper review.
- The stack smoke reflects the actual browser authentication flow.
- The overview remains demonstrative: estimated geometry, prepared evidence,
  and field authorization boundaries are unchanged.
- Later increments should extract the repeated navigation shell and simplify
  the remaining dense pages without changing their domain contracts.
