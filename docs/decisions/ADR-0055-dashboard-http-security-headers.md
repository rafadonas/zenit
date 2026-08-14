# ADR-0055: Dashboard HTTP security header baseline

- Status: accepted
- Date: 2026-08-14

## Decision

Apply a single reviewed security-header set to every Next.js dashboard route.
The baseline blocks framing, cross-origin base and form targets, MIME sniffing,
referrer disclosure, unnecessary browser sensors, DNS prefetching, and
cross-origin opener sharing.

Keep the policy in `next.config.ts` and assert exact header names, values, and
the global path rule with the existing Vitest suite. Confirm the configured
headers in a local HTTP response after implementation.

## Consequences

The dashboard gains fail-closed browser protections without changing API
contracts, cookies, CSRF checks, data status, or operational authorization.

The CSP is intentionally partial because the current Next.js rendering path has
inline framework scripts and no nonce pipeline. A complete `script-src` policy,
public-edge verification, TLS termination, and HSTS remain required before an
operational deployment.
