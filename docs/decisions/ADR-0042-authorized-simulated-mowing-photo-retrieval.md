# ADR-0042: Authorized simulated mowing-photo retrieval

- Status: accepted
- Date: 2026-08-12

## Context

ADR-0040 stores exact post-service photo bytes in application-encrypted,
versioned object storage. Direct object-store access would bypass road-scoped
authorization, decryption, integrity checks, audit evidence, and the simulated
post-service labels required before any future human review.

## Decision

Allow only an active manager or supervisor with a current non-simulated role on
the photo's road to retrieve an uploaded simulated post-service photo through
`GET /v1/mowing-media/{photo_id}`. Select the immutable receipt and exact object
version, authenticate AES-256-GCM, then verify plaintext byte size and SHA-256.

After integrity verification and before delivery, append one
`prepared_mowing_post_service_photo_access_event`. PostgreSQL repeats the exact
receipt, active actor, road role, post-service scope, simulated/unverified
labels, and every false operational, execution, training, and reporting gate.

Use the same not-found response for absent and unauthorized photos. Return
successful content with `no-store`, `private`, `nosniff`, checksum, phase,
scope, simulated status, unverified status, and all non-operational headers.
Never expose object-store coordinates, versions, ETags, or encryption metadata.

## Consequences

- A future human-review client can receive the exact uploaded bytes without
  object-store credentials.
- Retrieval proves neither safe image decoding nor quality, ruler visibility,
  location, vegetation condition, mowing, effectiveness, or completion.
- Browser presentation, review decisions, retention, EXIF handling, and
  decoder/malware checks remain separate P0 increments.
