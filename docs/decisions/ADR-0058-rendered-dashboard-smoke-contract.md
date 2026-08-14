# ADR-0058: Rendered dashboard smoke contract

- Status: accepted
- Date: 2026-08-14

## Decision

Add stable, non-visual page markers to the server-rendered corridor and login
entry points. Require the tracked MVP stack verifier to confirm UTF-8 HTML and
the expected marker after each HTTP 200 response.

Keep the check read-only and unauthenticated. It must not create a session,
submit decisions, or infer browser-side interactivity. Its purpose is to catch
upstream connection failures and framework error documents that can still
produce a reachable dashboard process or an HTTP 200 response.

## Consequences

The Compose smoke gate now verifies that the dashboard rendered its expected
page content after loading the API-backed corridor, rather than checking only
port availability. A stale internal API connection or an unrelated HTML page
causes the release check to fail with a specific message.

This contract does not replace browser automation, visual regression,
JavaScript hydration, accessibility review, or an authenticated end-to-end
workflow. Those require separate checks appropriate to their risk and scope.
