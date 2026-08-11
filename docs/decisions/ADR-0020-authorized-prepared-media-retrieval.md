# ADR-0020: Authorized prepared-media retrieval

- Status: accepted
- Date: 2026-08-11

## Context

Uploaded point photos are encrypted and checksum-bound, but no application
boundary could retrieve them for a future human quality review. Direct object
store access would bypass road-scoped authorization, application decryption,
integrity verification, and prepared-data labels.

## Decision

Allow an active manager or supervisor with a current non-simulated role on the
photo's road to retrieve an uploaded prepared photo through the API. Select the
immutable receipt and exact object version, authenticate AES-256-GCM, and
recheck plaintext byte size and SHA-256 before returning any content.
Persist an append-only access event only after those integrity checks pass;
PostgreSQL repeats the active-user, road-role, exact-receipt, and safety-label
guards before the API can deliver the response.

Return unauthorized and absent photos through the same not-found boundary.
Mark successful responses `no-store`, `private`, and `nosniff`, and expose
prepared, unverified, ruler-not-validated, and non-official status headers.
Never expose object-store coordinates or encryption metadata.

## Consequences

- Human review clients can obtain the exact received bytes without object-store
  credentials.
- Retrieval does not itself validate decoding, malware safety, EXIF privacy,
  ruler presence, image quality, location, or vegetation height.
- Browser presentation, reviewer decisions, retention, legal hold, and audited
  quality/ruler outcomes remain separate increments.
