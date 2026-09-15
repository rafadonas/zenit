# QA-001: E2E journey matrix and integration baseline

- Assessment date: 2026-09-13
- Base revision: `14ac506`
- Owner: Rafael
- Target: P0 evaluation demonstration
- Scope: reproducible manual journeys plus the automated integration checks that
  already exist in the repository
- Status: baseline defined; operational or field-pilot certification remains
  out of scope

## Safety and data boundary

This matrix validates the demonstrative flow only. The road axis is estimated,
the satellite layer is partially cached, inspections are prepared, mowing is a
simulated rehearsal, and post-service evidence is simulated. No scenario in
this document authorizes field work, promotes data to operational history,
produces an official report, or makes data eligible for model training.

Use a fresh local stack and repository fixtures only. Do not use files from
`data/raw/`, personal data, real credentials, or unapproved external services.
The spreadsheet reference date is 2025-03-28 and must never be described as the
current vegetation condition.

## Coverage model

| ID | Journey or boundary | Manager | Supervisor | Web | API | Mobile | Offline | Accessibility | Current evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E2E-01 | Enter the prepared dashboard and inspect corridor evidence | primary | read-only role context | yes | yes | no | no | manual | partial automation + manual |
| E2E-02 | Review a recommendation and create a prepared inspection order | primary | allowed-policy rerun | yes | yes | no | no | manual | API/component automation + manual |
| E2E-03 | Complete prepared inspection capture and retry synchronization | review | no action | summary only | yes | primary | yes | manual | API/mobile automation + manual |
| E2E-04 | Review inspection evidence and generate a prepared summary | primary | allowed-policy rerun | yes | yes | no | no | manual | API/component automation + manual |
| E2E-05 | Prepare and review a non-executable mowing plan | primary | secondary context | yes | yes | read-only | cached view | manual | API/component/mobile automation + manual |
| E2E-06 | Run simulated mowing rehearsal and synchronize post-service evidence | review | no action | history only | yes | primary | yes | manual | API/mobile automation + manual |
| E2E-07 | Review simulated post-service evidence, exception, and CSV export | primary | allowed-policy rerun | yes | yes | no | no | manual | API/component automation + manual |
| E2E-08 | Reject unauthenticated, unauthorized, conflicting, and invalid requests | yes | yes | yes | primary | yes | yes | keyboard error recovery | automated boundaries + manual |
| E2E-09 | Operate dashboard critical paths without mouse and at 200% zoom | yes | yes | primary | no | no | no | primary | manual gap |
| E2E-10 | Preserve encrypted drafts through restart, logout uncertainty, and retry | no | no | no | sync boundary | primary | primary | mobile semantics manual | mobile automation + device gap |

`Primary` identifies the layer or role where the scenario is exercised. `Manual`
means the user-visible journey still needs a human browser or device run; it is
not evidence that the scenario currently passes.

## Reproducible environment

1. Start from a clean checkout of the assessed revision with no `.env` values
   copied into evidence.
2. Use the CI Compose overlay so the database and object storage begin empty:

   ```bash
   export COMPOSE_PROJECT_NAME=zenit-qa-001
   export COMPOSE_FILE=compose.yaml:compose.ci.yaml
   docker compose up --build --wait --wait-timeout 240
   ```

3. Run the automated fresh-stack boundary:

   ```bash
   python scripts/verify_mvp_stack.py --expect-empty
   ```

   If another local stack owns the default host ports, use an untracked Compose
   override with alternate host ports and pass the matching `--api-base` and
   `--dashboard-base` values to the verifier. Do not stop or reuse the other
   stack: reaching a populated API invalidates the fresh-stack assertion.

4. For populated manual journeys, seed only the repository's clearly labeled
   demonstrative fixtures using the documented local process. Record the exact
   seed command and source revision in the test evidence.
5. Use the manager dashboard at `http://localhost:3000` and the supervisor
   dashboard at `http://localhost:3002`. Never expose these local prepared
   identities outside the isolated development environment.
6. Remove the isolated stack after the run:

   ```bash
   docker compose down --volumes --remove-orphans
   ```

Do not reuse a development database for a baseline run. A fresh database makes
empty-state, migration, idempotency, and test-data provenance reproducible.

## Journey procedures

### E2E-01 - prepared dashboard and corridor

**Precondition:** fresh stack for empty/error states; demonstrative seed for the
populated state.

1. Open the manager dashboard and enter through the local prepared identity.
2. Confirm that the overview and corridor expose data status, source/reference
   date, quality, and limitations near the result.
3. Open the corridor with tiles available, then repeat with the tile endpoint
   unavailable.
4. Confirm the segment/list information remains usable without tiles and that
   historical N1/N2/N3 values are not presented as current measurements.
5. Repeat with the supervisor dashboard and confirm the visible role context.

**Pass:** both roles can inspect only their permitted prepared context; tile
failure does not remove the non-map evidence; no text implies current or
operational data.

### E2E-02 - recommendation review and prepared inspection order

1. As manager, open a recommendation and verify sensor/product, quality,
   explanation, confidence interpretation, and rule/model version.
2. Exercise accepted, rejected, and adjusted decisions on separate records.
   Adjusted and rejected decisions must require the applicable rationale and an
   adjusted decision must require a replacement recommendation.
3. Create a prepared inspection order from an eligible human review and repeat
   the submission with the same idempotency key.
4. Repeat an independent allowed case as supervisor; then attempt the decision
   without authentication and with an identity that has no allowed role for the
   target road.

**Pass:** the server actor and append-only review are preserved; replay is
idempotent or returns an explicit conflict; unauthenticated/unauthorized calls
fail; the response states that neither review nor order authorizes field work.

### E2E-03 - offline prepared inspection and synchronization

1. Sign in online on the Android app and download the prepared order.
2. Disable network access, confirm the order, and record the three planned
   measurements and required prepared photo manifests.
3. Close and restart the app before submission; confirm the encrypted draft and
   stable event identifiers remain available to the same user.
4. Submit while offline, restore network, and retry twice.
5. Exercise a rejected event and a `409` conflict and inspect the local outcome.

**Pass:** offline state is explicit, no draft is lost on restart, manifest is
accepted before photo bytes, retries do not duplicate accepted events, and
rejected/conflicting outcomes remain recoverable without last-write-wins.

### E2E-04 - photo review and prepared inspection summary

1. As manager, open the inspection photo-review queue and review success and
   unavailable-image cases.
2. Confirm metadata, content checksum, provenance, and the human decision remain
   readable even when image retrieval fails.
3. Attempt summary generation before all required human reviews are accepted,
   then after the gate is satisfied.
4. Export the resulting CSV and inspect status, provenance, and audit metadata.
5. Repeat an independent allowed review as supervisor and a denied case with no
   scoped road role.

**Pass:** failed media access does not hide the case; pixels are never treated
as measured height; the summary is gated by the required evidence; the export
remains prepared and is not an official report.

### E2E-05 - non-executable mowing planning

1. Create a post-inspection proposal and record its human review.
2. Create the prepared mowing order, candidate resource plan, manual readiness
   assessment, and planning-only approval in order.
3. Attempt each transition out of order, with stale input, and under an
   unauthorized role.
4. Open the order on mobile while offline and verify it is read-only and visibly
   labeled as prepared/non-executable.

**Pass:** prerequisites fail closed; role checks are enforced by the API; every
decision retains actor, policy/version, and rationale; no planning action
authorizes mowing.

### E2E-06 - simulated mowing and post-service synchronization

1. Download an eligible prepared mowing order, then disable network access.
2. Confirm, start with simulated location, pause/resume in balanced order, and
   finish the rehearsal.
3. Record exactly three simulated post-service heights and one photo manifest
   per planned point; close and restart the app during the flow.
4. Restore network, synchronize manifests, upload encrypted bytes, and repeat
   requests with stable identifiers.

**Pass:** invalid lifecycle sequences fail; restart preserves the encrypted
draft; manifests precede bytes; replay is idempotent; all synchronized evidence
remains `simulated`, unverified, and ineligible for operations.

### E2E-07 - post-service review, exception, and export

1. As manager, review all simulated post-service photos and verify that quality
   and ruler visibility are separate human fields.
2. Attempt summary creation before three measurements and three accepted visual
   reviews exist, then satisfy the gate and retry.
3. Create the threshold exception, record accepted/rejected/adjusted decisions on
   separate cases, and export the summary CSV.
4. Repeat an independent allowed review as supervisor; then attempt access and
   review without authentication and with no allowed role for the target road.

**Pass:** summary and exception gates fail closed; decisions are append-only;
media access is audited; export preserves simulation/provenance labels and is
not eligible for official reporting.

### E2E-08 - common failure contract

For every write used above, sample at least one `401`, `403`, `409`, `422`, and
dependency-unavailable path where the endpoint supports it. Confirm that:

- errors use the stable envelope and a matching UUID correlation header;
- login failure does not enumerate accounts and throttling is persistent;
- request bodies cannot forge actor identity or eligibility flags;
- a duplicate idempotency key never silently creates a second event;
- loss of PostgreSQL or MinIO makes readiness fail closed;
- the UI gives a recoverable, keyboard-reachable message without exposing a
  token, secret, stack trace, object key, or personal data.

### E2E-09 - dashboard accessibility pass

Repeat E2E-01, E2E-02, E2E-04, E2E-05, and E2E-07 in a supported browser:

1. Use keyboard only and confirm the skip link, visible focus, logical order,
   accessible names, and no focus trap.
2. Test at 200% zoom at widths 360, 768, 1024, and 1440 px without loss of
   content or action.
3. Enable reduced motion and confirm loading/status feedback remains clear.
4. With a screen reader, check dynamic errors, review forms, status changes, and
   map/list equivalence.

**Pass:** every critical action and error recovery is available without mouse or
color alone. Record browser, version, OS, viewport, zoom, assistive technology,
role, route, and result. This is a manual audit, not a WCAG conformance claim.

### E2E-10 - mobile recovery pass

On a representative Android device or emulator, repeat the offline parts of
E2E-03 and E2E-06 with airplane mode, timeout, `401`, `409`, process termination,
and relaunch. Verify readable text scaling, semantic labels, focus order, and
touch targets. Test logout both online and offline and confirm unacknowledged
encrypted data is not silently deleted.

## Existing automated baseline

| Gate | Command | What it establishes | Important limit |
| --- | --- | --- | --- |
| Python/API | `ruff check .` and `pytest` | domain, API, contracts, migrations, security failures, and smoke verifier | mostly in-process; not a complete user journey |
| OpenAPI | `python scripts/export_openapi.py --check` | versioned API document matches the implementation | does not validate consumer UX |
| Dashboard | `npm run dashboard:lint`, `npm run dashboard:typecheck`, `npm run dashboard:test`, `npm run dashboard:build` | typed build, component/routes, security and automated accessibility baseline | no real browser, keyboard, zoom, or assistive technology |
| Mobile | `dart format --output=none --set-exit-if-changed lib test`, `flutter analyze`, `flutter test` | offline drafts, lifecycle, retry, rejection/conflict, and widget contracts | no representative device or OS interruption audit |
| Android build | CI debug APK build and `scripts/verify_android_apk.py` | package metadata, SDK constraints, HTTPS placeholder and debug signature | demonstrative artifact only |
| Fresh stack | Compose schema checks and `python scripts/verify_mvp_stack.py --expect-empty` | migrated PostGIS/MinIO/API/dashboard readiness plus 25 public/protected HTTP boundaries | empty stack; no authenticated browser/mobile journey |

The current CI is a strong integration baseline, but it is not a full E2E suite.
Choosing a browser/device automation framework is a separate decision and is not
authorized by QA-001.

## Baseline result record

Record one row per execution. Do not replace a failure with a later passing run;
append the rerun and link both to the same defect.

| Date/time (UTC) | Revision | Environment | Gate/scenarios | Result | Evidence or defect |
| --- | --- | --- | --- | --- | --- |
| 2026-09-13 | `14ac506` | Python 3.14.7 local checkout | Ruff, 428 Pytest tests, OpenAPI 36-path check | PASS | command output retained in QA-001 task |
| 2026-09-13 | `14ac506` | Node.js local checkout | lint, typecheck, 42 Vitest files/137 tests, production build | PASS | command output retained in QA-001 task |
| 2026-09-13 | `14ac506` | Flutter local checkout | format, analyze, 61 tests | PASS | command output retained in QA-001 task |
| 2026-09-13 | `14ac506` | isolated Compose project on default ports | fresh-stack smoke | ENVIRONMENT FAIL | port 9000 was owned by the existing development stack; verifier rejected its non-empty API; isolated resources removed |
| 2026-09-13 | `14ac506` | isolated Compose project on alternate host ports | health plus 25 empty/public/protected HTTP and rendered-dashboard checks | PASS | all services healthy; isolated containers, network, and volumes removed |
| 2026-09-13 | `14ac506` | browser/device | E2E-01 through E2E-10 manual procedures | NOT RUN | retained as explicit manual baseline gaps |

Manual evidence must contain no secrets or personal data. Store large or
temporary screenshots outside Git; if a small image is approved for tracking,
redact it and record its purpose and source revision.

### Targeted login/session regression

The Rafael validation card for the historical login failure is covered by the
targeted route/API suite and bounded local fixed-session/logout check recorded
in [`login-session-regression-2026-09-15.md`](login-session-regression-2026-09-15.md).
The browser/device accessibility gap remains intentionally separate from this
route-level regression result.

## Exit criteria and known gaps

QA-001 is complete when this matrix is reproducible, each required dimension is
owned by a scenario, the existing automated gates pass on the ticket branch,
and manual gaps are explicitly retained. It does not require selecting a new
automation tool.

Known gaps after this baseline:

- authenticated browser-to-API-to-database journeys are manual;
- keyboard, zoom, screen-reader, tile outage, and both roles require manual runs;
- mobile process death, OS permissions, airplane mode, and accessibility require
  a representative emulator/device run;
- no external-service or production/staging validation is permitted by this
  ticket;
- the Docker dashboard build reported two moderate and one high npm dependency
  audit findings; triage belongs in SEC-001 and no dependency was changed here;
- operational identity, official geometry, field policy, and official reporting
  remain blocked by external decisions.
