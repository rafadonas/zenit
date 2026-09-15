# Login and session regression evidence

- Ticket: validation card for login, session, and failure recovery
- Owner: Rafael
- Revision under test: `77d1394` (post-merge `main`)
- Scope: QA-001 E2E-08 authentication failures and the WEB-004 login/session
  contract; this record does not certify a production identity provider.
- Data boundary: local prepared identities only; no real credentials, personal
  data, or external service was used.

## Result

The source revision passes the targeted login/session regression suite. The
checks cover:

- same-origin and loopback-origin login, including Chrome's opaque local origin;
- generic invalid-credential, throttling, invalid-request, and unavailable-
  service recovery messages;
- safe `return_to` allowlisting, including rejection of external and API paths;
- fixed local-session creation with strict HttpOnly/SameSite cookies;
- CSRF-protected logout, remote-revocation fallback, and cookie clearing;
- proxy behavior for an existing session, an expired/missing session, and the
  fixed local demo entry point; and
- the absence of bearer tokens or upstream private details in login UI output.

## Reproducible evidence

| Check | Command | Result |
| --- | --- | --- |
| Dashboard login/session routes | `npm --workspace @zenit/dashboard run test -- src/lib/login-route.test.ts src/lib/fixed-session-route.test.ts src/lib/logout-route.test.ts src/lib/login-messages.test.ts src/lib/login-experience.test.ts src/lib/session-security.test.ts src/proxy.test.ts` | **PASS** — 7 files, 41 tests |
| API authentication and persistent throttle | `.venv/bin/pytest -q services/api/tests/test_auth.py services/api/tests/test_login_throttle.py` | **PASS** — 22 tests |
| Fresh main CI after merge | GitHub Actions run `34988355677` | **PASS** — API, dashboard, mobile, and Compose smoke |
| Live local fixed-session/logout boundary | fixed-session `303` with 2 strict cookies; logout `303` to `/login?status=signed-out` with 2 `Max-Age=0` clears | **PASS** |

The live boundary was executed against the already-running local stack without
printing cookie or token values. Its dashboard image was built before the
current WEB-004 source and therefore is not used as evidence for the rendered
login recovery page; the current source behavior is covered by the route and
proxy tests above and by the fresh CI build.

## Acceptance and limits

The historical “login test error” is no longer reproducible in the current
source revision: all targeted route, security, UI-contract, and API auth tests
pass, and the live logout boundary returns the expected safe redirect and
clears both cookies.

QA-001 still records manual browser keyboard/zoom/screen-reader checks as a
separate gap. This ticket does not claim a production IdP, MFA, password
recovery, or operational identity; those remain outside the academic MVP.
