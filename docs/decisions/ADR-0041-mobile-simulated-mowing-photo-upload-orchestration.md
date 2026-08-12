# ADR-0041: Mobile simulated mowing-photo upload orchestration

- Status: accepted
- Date: 2026-08-12

## Context

ADR-0040 created a verified encrypted upload boundary for simulated mowing
post-service photos. The Flutter client still stopped after synchronizing each
manifest, because sending bytes before persistent manifest acceptance would
break the server provenance checks.

## Decision

Expose a separate, explicit mobile upload action only after all three
post-service photo manifests have persistent accepted results. Send the exact
JPEG or PNG bytes retained in the encrypted vault with the registered logical
device identifier to `POST /v1/mowing-media/{photo_id}`.

Validate the complete response, including the exact photo identifier, checksum,
size, media type, post-service scope, simulated status, unverified status, and
every false operational, execution, training, and official-reporting flag.
Persist `uploaded_unverified` locally after each accepted response before
continuing to the next photo.

On retry, skip only photos with a locally persisted upload receipt. Keep the
encrypted bytes in the vault, and continue treating an acknowledged manifest
without that receipt as pending local evidence. Server-side idempotency remains
the fallback when the response was lost before local persistence.

## Consequences

- A partial network failure resumes from the first locally unconfirmed photo.
- Upload proves server possession of exact bytes but not location, ruler
  visibility, image quality, vegetation condition, mowing, or completion.
- The action remains user-triggered and never authorizes field work or changes
  the simulated evidence classification.
- Background transfer, retrieval, access auditing, retention, decoder/malware
  checks, EXIF handling, and human review remain separate P0 increments.
