# ZENIT incremental threat model

- Assessment date: 2026-09-13
- Ticket: SEC-001
- Assessed revision: `eb899e4`
- Scope: P0 evaluation demonstration and known P1 boundaries
- Method: asset and trust-boundary review with STRIDE-oriented threat discovery
- Decision boundary: risks may be accepted only for the isolated P0
  demonstration; this document does not approve internet exposure, field work,
  an operational pilot, model training, or official reporting

## Purpose and maintenance

This is the security baseline for the architecture that exists in the
repository. Update it whenever identity, authorization, media processing,
external maps/providers, AI tooling, build dependencies, deployment boundaries,
or data-eligibility rules change. A risk marked accepted here is accepted only
within the local demonstrative scope recorded in `docs/mvp-readiness.md`.
Operational acceptance requires an authorized human owner and a separate,
versioned decision.

Risk ratings combine likelihood and impact using `low`, `medium`, `high`, and
`critical`. Residual risk is the rating after current controls. `Blocked` means
the P0 demonstration may continue, but the affected capability must not cross
into operational use.

## Security invariants

- AI, a recommendation, or a planning action never authorizes mowing.
- Prepared, estimated, simulated, and inconclusive data cannot silently become
  real, training-eligible, operational, or official-reporting data.
- The server derives actor identity from an active session and enforces current
  road-scoped authorization; clients cannot supply or promote identity.
- Human decisions, policy/rule/model versions, provenance, and access events
  remain auditable and append-only where the domain requires it.
- Raw evidence is immutable. Derived evidence retains checksums and lineage.
- Passwords, bearer tokens, encryption keys, provider keys, and object-store
  coordinates must not appear in source, client payloads, logs, or screenshots.
- Mobile manifests precede media bytes, and retries reuse stable identifiers.
- Losing a dependency must fail readiness or the affected operation closed.

## Assets

| ID | Asset | Security property |
| --- | --- | --- |
| A-01 | Password hashes, JWT signing material, sessions, CSRF values, and provider keys | confidentiality, integrity, revocability |
| A-02 | Road-scoped roles, human approvals, policy versions, and audit events | integrity, authenticity, non-repudiation |
| A-03 | Raw sources, normalized layers, checksums, lineage, and data-status labels | integrity, provenance, correct classification |
| A-04 | Field and post-service measurements, photo manifests, encrypted bytes, and access history | confidentiality, integrity, availability |
| A-05 | Mobile vault key, cached orders, drafts, stable event IDs, and sync outcomes | confidentiality, integrity, recoverability |
| A-06 | Map requests, location context, external-provider quota, and attribution | privacy, availability, contractual compliance |
| A-07 | Source code, lockfiles, CI workflows, container images, releases, and build provenance | integrity, reproducibility |
| A-08 | Model/rule outputs and the gates for field execution, training, history, and reports | integrity, safety |

## Actors

| Actor | Capability and trust assumption |
| --- | --- |
| Anonymous user | Can reach public/read-only HTTP routes; is untrusted. |
| Prepared manager or supervisor | Has a local demonstrative identity and selected road roles; may be malicious, mistaken, or compromised. |
| Mobile user and registered device | Holds a short-lived session and encrypted local state; the device can be lost or compromised. |
| Maintainer/reviewer | Can change code, dependencies, policies, and evidence through Git; requires peer review. |
| Database/object-storage administrator | Has privileged infrastructure access; separation and monitoring are not yet production-grade. |
| External map or satellite provider | Supplies untrusted availability, metadata, images, and responses; may observe requests. |
| Dependency or registry publisher | Supplies packages, actions, SDKs, and container images; may be compromised upstream. |
| AI coding agent/tool | Reads untrusted repository and external content and may propose tool actions; must not become an approval authority. |
| External attacker | May guess credentials, replay tokens, forge requests, upload hostile bytes, exhaust resources, or exploit dependencies. |

## Trust boundaries and data flow

```text
anonymous/authenticated browser
        | TB-01 HTTPS + cookies + CSRF
        v
Next.js dashboard -------- TB-06 --------> external map tiles
        | TB-02 server-held bearer token
        v
FastAPI API <------------- TB-03 ---------- mobile app + encrypted vault
   |            |
 TB-04        TB-05
   |            |
PostgreSQL   private versioned object storage
   |
   +------------- TB-07 -------------> satellite/provider APIs

maintainer/AI agent -------- TB-08 --------> Git, CI, registries, build outputs
```

| Boundary | Required protections | Current limitation |
| --- | --- | --- |
| TB-01 browser/dashboard | exact origin, strict cookies, CSRF, security headers, HTTPS outside local use | partial CSP; no approved public edge or HSTS |
| TB-02 dashboard/API | bearer token remains server-side; API rechecks active session and RBAC | local prepared identity is not corporate identity |
| TB-03 mobile/API | HTTPS release URL, bearer session, device binding, idempotency, fail-closed schemas | no device attestation, remote administrative revocation, or operational offline unlock policy |
| TB-04 API/database | parameterized queries, constraints, append-only events, migrations, least privilege | local Compose credential and role separation are not production controls |
| TB-05 API/object storage | application AES-256-GCM, exact version/checksum, private bucket, access audit | key custody, malware/decoder checks, EXIF privacy, retention, and restore are unresolved |
| TB-06 browser/map provider | configuration allowlist, attribution, privacy and outage behavior | public-provider policy and referrer behavior are inconsistent and not operationally approved |
| TB-07 backend/provider | backend-only secrets, bounded requests, normalized untrusted responses, quota controls | Planet foundation is discovery-only; quota, downloads, checksums, and proxy/cache are absent |
| TB-08 maintainer/AI/supply chain | sandbox/approval, branch protection, peer review, lockfiles, read-only CI permissions | actions/images use mutable tags and dependency scanning is incomplete |

## Threat register

| ID | STRIDE | Threat and impact | Current controls and evidence | Residual | Treatment |
| --- | --- | --- | --- | --- | --- |
| AUTH-01 | S/D | Credential guessing or expensive password-hash abuse compromises or denies a local account. | Argon2 hashes; generic failures; PostgreSQL/HMAC throttle; `services/api/tests/test_auth.py` and `test_login_throttle.py`. | medium | Accepted for isolated P0; corporate IdP, MFA, perimeter control, recovery, and monitoring block internet exposure. |
| AUTH-02 | S/E | A stolen or replayed bearer token acts as the victim. | 30-minute tokens; issuer/audience/JTI validation; persisted session registration and logout revocation; active-user recheck; HttpOnly dashboard cookie. | medium | Accepted for isolated P0; TLS and administrative/session risk controls required for P1. |
| AUTH-03 | S | Offline logout cannot revoke a copied token while the API is unreachable. | Local access is cleared, uncertainty is shown, and the token expires; covered by `apps/mobile/test/offline_workflow_test.dart`. | medium | Accepted for P0 only; device/admin revocation is blocked for pilot. |
| WEB-01 | T/E | CSRF, actor forgery, or browser token theft creates a human decision under the wrong identity. | SameSite strict/HttpOnly cookie, exact-origin and constant-time CSRF checks, field allowlists, server-derived actor, API RBAC; dashboard session/security tests. | low | Monitor; retest at the deployed edge before P1. |
| WEB-02 | T/I | Script injection or browser policy gaps expose session context or alter decisions. | React escaping, form allowlists, anti-framing/nosniff/referrer/permissions headers, partial CSP; `security-headers.test.ts`. | medium | Complete nonce/hash CSP and edge TLS/HSTS before public exposure. |
| AUTHZ-01 | E | Hidden UI controls are bypassed and a user acts outside the assigned road or policy. | API and PostgreSQL independently verify active actor, road role, target, and immutable policy version; negative `401/403` endpoint tests. | low | Accept for P0; keep authorization server-side in every new endpoint. |
| AUTHZ-02 | T/R | A client forges reviewer identity, operational flags, or supersession history. | Extra fields are rejected; actor comes from session; append-only decisions and idempotency hashes; database false-value constraints; API/mobile negative tests. | low | Accept for P0; contract changes require Rafael plus consumer review. |
| MEDIA-01 | T/D | Oversized, mismatched, corrupt, or replayed uploads exhaust resources or replace evidence. | JPEG/PNG and 25 MiB limits; authenticated manifest/device/role gate; SHA-256, size and type match; stable IDs; versioned receipts; idempotent content verification. | medium | Add ingress/body limits and resource monitoring before P1. |
| MEDIA-02 | E/I/D | A hostile image exploits a decoder, carries malware, or exposes EXIF faces/plates/location. | Bytes are not interpreted as height; encrypted storage and human review keep evidence non-operational. No decoder, malware, or EXIF sanitization gate exists. | high | Blocked for operational/official use until safe decoding, scanning, anonymized copies, retention, and legal-hold policy exist. |
| MEDIA-03 | I/T | Object-store disclosure, direct access, or tampering exposes or substitutes photos. | Private versioned bucket; application AES-256-GCM; exact object version; decryption plus checksum/size verification; same not-found boundary; no-store/nosniff; append-only access events. | medium | Key custody, rotation, backup/restore, storage IAM, and centralized audit remain P1 blockers. |
| VAULT-01 | I/E | Lost, rooted, or malicious device extracts cached orders, drafts, tokens, or the vault key. | AES-256 Hive vault; random key in Android secure storage; password not stored; Android backup/transfer disabled; user-bound records and integrity checks. | high | Blocked for pilot until device enrollment/revocation, attestation/MDM decision, key policy, and representative-device review. |
| VAULT-02 | T/R | Retry, process death, account switching, or conflict silently loses or duplicates offline evidence. | Stable UUIDs, persistent batches/outcomes, manifest-before-bytes order, checksum validation, user isolation, explicit rejected/conflict states; mobile offline tests. | medium | Accepted for P0; device/process-death E2E remains manual in QA-001. |
| MAP-01 | I/D | External tiles reveal viewer IP/location context, become unavailable, or violate provider usage/attribution policy. | OSM attribution; no offline download/prefetch; map data is read-only and non-operational; list/error expectations in QA-001. | medium | Block public/high-volume use until a compliant provider/proxy/cache and privacy policy are approved. |
| MAP-02 | T | A configurable tile endpoint or provider content becomes an untrusted browser input. | Raster-only MapLibre use, no provider credential in browser, global browser headers. | medium | Allowlist schemes/hosts and verify browser failure behavior before P1. |
| PROV-01 | T/R | Source or derived geometry/classification is altered, misattributed, or presented as current. | Immutable raw policy, source SHA-256, lineage/import runs, explicit SRID/status/reference date, conservative `unknown`, and data-quality reports. | medium | Inferred KMZ mapping and estimated axis remain blocked pending data-owner validation. |
| SAFETY-01 | E/T | Prepared/simulated evidence is promoted to training, an official report, history, or field authorization. | Typed false flags in API/mobile, database constraints, human review, versioned policies, UI warnings, and extensive negative tests. | low | Accepted for P0 only; operational enablement requires a separate reviewed design and authorized approval. |
| AI-01 | S/T/I | Prompt injection in repository files, issues, provider responses, or source documents tricks an AI tool into revealing secrets or changing protected state. | `AGENTS.md` scope rules; read-first protocol; no secret printing; sandbox/approval expectation; branch/PR review; raw-data immutability; AI has no mowing authority. | medium | Treat all retrieved content as data, not instructions; require human review and explicit authority for network, dependencies, destructive actions, and production changes. |
| AI-02 | E | A model confidence value is treated as exact height or silently authorizes mowing. | Confidence semantics are documented; low confidence normally creates inspection; recommendations and approvals are separated; field/report/training gates are false. | low | Accept for P0; model promotion remains blocked behind validated data, shadow mode, and human gates. |
| SUPPLY-01 | T/E | A compromised package, action, registry, or container image executes during development/CI/build. | Committed npm/Flutter lockfiles; constrained Python requirements; minimal CI `contents: read`; peer-reviewed changes; no production secret requirement in ordinary CI. | medium-high | Pin actions/images by digest where feasible, add approved multi-ecosystem scanning and artifact provenance before P1. |
| SUPPLY-02 | D/I | Known development/test dependency advisories expose files or consume CPU in tooling. | `npm audit` on 2026-09-13 identified GHSA-82fw-gwwq-j7x9 in Vitest tooling and GHSA-2883-xcg3-v3hh in `js-yaml`; both report fixes available, while `npm audit --omit=dev` reports zero production findings. | high on an untrusted CI runner | Open a dependency-remediation ticket; do not accept for a shared/untrusted CI runner. No dependency change is authorized by SEC-001. |
| AVAIL-01 | D | PostgreSQL, MinIO, API, or dashboard dependency loss is reported as healthy or causes unsafe continuation. | Bounded dependency probes; required services fail readiness closed; Compose health dependencies; 25-contract fresh-stack smoke. | low | Accept for P0; SLOs, alerts, redundancy, backup, and restore remain OPS-001/OPS-002 blockers. |

## Findings requiring follow-up

### F-01 - dependency advisories

Current `npm audit` reports one high and two moderate vulnerability entries:

- `js-yaml` before 4.3.2: CPU exhaustion through merge-key processing
  (GHSA-2883-xcg3-v3hh);
- `vitest` and transitive `@vitest/mocker` before 4.1.11: path traversal or
  arbitrary file read in redirect mocks (GHSA-82fw-gwwq-j7x9).

The report marks fixes as available. Remediation must be a separate dependency
ticket because it changes the lockfile and needs the full dashboard and CI gate.
`npm audit --omit=dev` reports no production dependency findings, so the known
exposure is currently in development/test tooling rather than the dashboard
runtime dependency set.
Until then, do not run repository-authored Vitest mocks or YAML processing from
untrusted contributions on a runner containing secrets.

### F-02 - map referrer-policy inconsistency

ADR-0066 says the browser may send an origin referrer to the OpenStreetMap tile
service, while the global dashboard baseline deliberately sends
`Referrer-Policy: no-referrer`. These cannot both describe the effective browser
behavior. Resolve the provider/privacy policy before public or sustained use;
do not weaken the global privacy header ad hoc. The P0 map remains a local,
low-volume, best-effort demonstration with attribution and no offline cache.

### F-03 - media and mobile operational blockers

Encryption and checksums protect stored bytes, but they do not provide safe
decoding, malware detection, EXIF/privacy handling, key recovery, device trust,
retention, or legal hold. These controls are mandatory before real field media
or an operational mobile rollout.

## Negative-test traceability

| Risk area | Existing automated evidence | Required next evidence |
| --- | --- | --- |
| Authentication/session | `test_auth.py`, `test_login_throttle.py`, dashboard login/logout/session tests | MFA/IdP, administrative revocation, proxy-aware abuse tests |
| Road authorization and actor integrity | recommendation, order, review, summary, media, and export API tests with `401/403/409/422` cases | populated cross-road E2E for manager and supervisor |
| CSRF/browser session | `session-security.test.ts`, route tests, proxy tests, security-header tests | real browser origin, cookie, CSP, keyboard, and expiry audit |
| Upload/retrieval | `test_media.py`, `test_mowing_media.py`, review tests | hostile decoder corpus, malware scan, EXIF/anonymization and size-at-ingress tests |
| Offline vault/sync | mobile domain and `offline_workflow_test.dart` | rooted-device assessment, airplane-mode/process-death/device-loss E2E |
| Provenance/safety gates | source/import/contract tests plus API/mobile false-flag tests | data-owner validation and explicit promotion-policy tests |
| External maps/providers | vegetation map and provider offline tests | tile outage/privacy/compliance test and provider quota/credential audit |
| AI/tooling | repository workflow rules and mandatory peer-reviewed PR | prompt-injection red-team cases with fake secrets and destructive-action denial |
| Supply chain | lockfiles, CI builds, release-evidence checks | advisory remediation, action/image pinning, SBOM/provenance and secret-isolated untrusted PR test |

## Risk acceptance record

| Scope | Decision | Authority/evidence | Expiry or review trigger |
| --- | --- | --- | --- |
| Isolated P0 evaluation demonstration | Accept low/medium residual risks described above while all operational/training/reporting gates remain false. | Project readiness decision in `docs/mvp-readiness.md`; technical controls and CI evidence. | Any architecture/control change, new external exposure, or 90 days, whichever comes first. |
| Internet-facing deployment | Not accepted. | Corporate identity, TLS/edge policy, monitoring, privacy, retention, and incident response are incomplete. | Reassess after API-002, OPS-001, and security controls are approved. |
| Real field/mobile/media pilot | Not accepted. | Device trust, real GPS/media privacy, key custody, safe decoding, retention, backup/restore, and operational policy are unresolved. | Reassess after human owners approve the pilot controls. |
| Model training or automated promotion | Not accepted. | No approved real dataset/ground truth or model promotion gate exists; demo/simulated data is prohibited. | Reassess after GEO/AI predecessors and formal human approvals. |
| Official report or mowing authorization | Not accepted. | Current artifacts and decisions are prepared/simulated and database/API gates explicitly deny these outcomes. | Requires a separate authorized operational decision; never inferred from this model. |

No entry in this table accepts risk on behalf of Motiva, a data owner, a privacy
owner, an operational manager, or a security authority. Unassigned P1 risks
remain blockers rather than silently inheriting Rafael as their acceptance owner.

## Review checklist

- Re-enumerate assets, actors, and boundaries after every architecture change.
- Link new high-impact threats to at least one negative automated test or an
  explicit blocked/manual verification.
- Verify that errors and logs contain correlation IDs but no credentials,
  personal data, object coordinates, or raw provider payloads.
- Confirm `data/raw/`, checksums, lineage, versions, and simulation labels remain
  unchanged unless an approved data ticket says otherwise.
- Re-run package advisories and review lockfile, action, SDK, and image changes.
- Review provider terms, quota, privacy, attribution, and outage behavior.
- Require a human security review for authentication, upload, privacy, key
  custody, dependency, CI, and AI-tooling changes.
- Never close a high/critical risk by relabeling prepared or simulated data.
