# ADR-0018: Verified encrypted prepared-media upload

- Status: accepted
- Date: 2026-08-09

## Context

ADR-0016 records checksum-bound photo manifests, and ADR-0017 retains the
corresponding bytes in the encrypted mobile vault. A manifest alone does not
prove server possession. The platform needs a bounded upload path without
presenting unreviewed images as field evidence or official data.

MinIO SSE-C requires TLS for every request. The Compose service uses an internal
HTTP endpoint for local development, so relying on SSE-C would either break the
local stack or encourage an unsafe transport exception.

## Decision

Accept JPEG and PNG uploads up to 25 MiB only after authentication and device
binding. Recheck the active actor, non-revoked device, current manager or
supervisor road role, and exact manifest checksum, byte size, and media type.

Encrypt each payload in the API with AES-256-GCM before object storage. Keep the
key outside the object store, write only ciphertext as `application/octet-stream`
to a private versioned media bucket, and bind the database receipt to the object
bucket, key, version, ETag, manifest, actor, device, and plaintext checksum.
Repeated uploads are idempotent only after authenticating and decrypting the
existing version and matching its content.

Require HTTPS object-storage endpoints in staging and production. Local
development may use internal HTTP because plaintext never crosses that boundary;
API transport still requires an appropriate deployment ingress policy.

Fix every receipt to `uploaded_unverified`, `not_validated`,
`prepared_unverified`, `prepared`, and non-official. Make receipts append-only.

## Consequences

- Server possession is independently recorded without claiming photographic
  quality, ruler validity, vegetation height, or operational authorization.
- An object-store disclosure does not expose plaintext without the separate
  application encryption key.
- Losing the encryption key makes stored media unrecoverable; production key
  custody, rotation, backup, and recovery procedures are required before pilot.
- Retrieval authorization, malware/decoder checks, EXIF privacy handling,
  retention/legal hold, quality review, ruler validation, and mobile upload
  orchestration remain separate reviewed increments.
