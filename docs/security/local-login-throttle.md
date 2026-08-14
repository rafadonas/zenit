# Local login throttle baseline

- Scope: provisional local MVP password authentication
- Status: persistent P0 baseline, not corporate identity

`POST /v1/auth/token` checks a PostgreSQL throttle before password hashing. The
default policy allows five failures in 900 seconds and then returns HTTP 429 for
900 seconds. The response includes `Retry-After`; the dashboard shows a generic
wait message.

| Setting | Default | Bounds |
| --- | ---: | ---: |
| `AUTH_LOGIN_ATTEMPT_LIMIT` | 5 | 2-20 |
| `AUTH_LOGIN_WINDOW_SECONDS` | 900 | 60-86400 |
| `AUTH_LOGIN_BLOCK_SECONDS` | 900 | 60-86400 |
| `AUTH_LOGIN_THROTTLE_POLICY_VERSION` | `local-login-throttle-v1` | 1-100 token characters |

The mutable `authentication_login_throttle` table contains only an HMAC digest,
counter, timestamps, and policy version. The append-only
`authentication_login_attempt` table records the digest, outcome, policy,
correlation ID, and event time. Neither table stores the submitted identifier or
password.

Changing `AUTH_SECRET_KEY` changes future digests and effectively abandons old
throttle state without deleting audit evidence. Retention, security-event
export, trusted proxy controls, and centralized monitoring remain required
before internet exposure.
