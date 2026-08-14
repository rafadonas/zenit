# Dashboard HTTP security headers

- Assessment date: 2026-08-14
- Scope: all Next.js dashboard routes
- Status: local P0 baseline, not a production edge-security policy

## Enforced headers

| Header | Value | Purpose |
| --- | --- | --- |
| `Content-Security-Policy` | `base-uri 'self'; form-action 'self'; frame-ancestors 'none'` | Blocks hostile base URLs, cross-origin form targets, and embedding. |
| `Cross-Origin-Opener-Policy` | `same-origin` | Isolates the dashboard browsing context from cross-origin openers. |
| `Permissions-Policy` | `camera=(), geolocation=(), microphone=()` | Prevents sensor access that the dashboard does not require. |
| `Referrer-Policy` | `no-referrer` | Prevents dashboard paths from being sent as referrer data. |
| `X-Content-Type-Options` | `nosniff` | Disables browser MIME sniffing. |
| `X-DNS-Prefetch-Control` | `off` | Disables speculative DNS prefetching. |
| `X-Frame-Options` | `DENY` | Provides legacy anti-clickjacking protection. |

The values are defined once in `apps/dashboard/next.config.ts`, applied to
`/:path*`, and asserted exactly by the dashboard Vitest suite. A local runtime
request to `/login` also confirmed all seven headers in the HTTP response.

## Deployment requirements

- Add a nonce- or hash-based `script-src` policy compatible with Next.js before
  treating CSP as complete. Do not add `unsafe-eval` to a production policy.
- Terminate TLS at an approved proxy and add HSTS there only after the hostname
  and certificate lifecycle are operationally controlled.
- Review opener and permissions policies before adding corporate identity,
  browser sensors, or cross-origin integrations.
- Retest headers at the public edge because a reverse proxy or CDN can remove,
  duplicate, or replace application headers.

These headers do not change prepared/simulated data status and do not authorize
field execution, model training, or official reporting.
