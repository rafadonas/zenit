# ADR-0040: Verified encrypted simulated mowing-photo upload

- Status: accepted
- Date: 2026-08-12

## Context

ADR-0038 persists checksum-bound post-service photo manifests and ADR-0039
retains their bytes in the encrypted mobile vault. A manifest proves neither
server possession nor image integrity, and the prepared inspection-photo
receipt cannot be reused without changing the simulated post-service labels.

## Decision

Add a separate authenticated `POST /v1/mowing-media/{photo_id}` boundary and an
append-only `prepared_mowing_post_service_photo_upload_receipt`. Accept JPEG or
PNG bytes up to 25 MiB only from the manifest's active actor and non-revoked
device while that actor retains a non-simulated manager or supervisor role on
the road. Require exact checksum, byte size, media type, phase, scope, and
non-operational manifest labels.

Reuse the application AES-256-GCM media primitive and private versioned bucket,
but store objects under a separate `simulated-mowing-post-service-photos`
namespace with `data-status=simulated`. Bind the immutable receipt to the exact
manifest event, object bucket, key, version, ETag, actor, device, plaintext
checksum, size, and type. An interrupted retry is idempotent only after the
existing ciphertext is decrypted and matched to the submitted plaintext.

Fix the receipt to `post_service`, `mowing_demo_post_service_only`,
`uploaded_unverified`, `not_validated`, `not_collected`, `simulated`, and
`simulated_unverified`. Keep operational approval, field authorization,
execution eligibility, model-training eligibility, and official-reporting
eligibility false.

## Consequences

- The receipt proves verified server possession of the submitted bytes without
  proving ruler visibility, image quality, location, vegetation condition,
  mowing, or completion.
- Object-store disclosure alone does not reveal plaintext without the separate
  application encryption key.
- Mobile upload orchestration, authorized retrieval, access auditing, retention,
  decoder/malware checks, EXIF handling, and human review remain separate P0
  increments.
