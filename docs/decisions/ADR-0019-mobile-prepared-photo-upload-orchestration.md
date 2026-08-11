# ADR-0019: Mobile prepared-photo upload orchestration

- Status: accepted
- Date: 2026-08-11

## Context

ADR-0018 created a verified encrypted media boundary, but the Flutter client
stopped after synchronizing photo manifests. Uploading before manifest
acceptance would fail provenance checks, while restarting all uploads after a
network interruption would obscure which receipts had already been confirmed.

## Decision

Expose photo upload as a separate, explicit mobile action after all three
manifest events have persistent accepted results. Send the exact encrypted-vault
JPEG or PNG bytes with the registered device identifier. Validate the complete
prepared upload response, then persist `uploaded_unverified` locally after each
photo before continuing to the next one.

Retry only photos that do not yet have a locally persisted upload receipt. Keep
the bytes in the encrypted vault and preserve `not_validated`,
`prepared_unverified`, `prepared`, and non-official labels. Treat an upload as
pending local evidence when deciding whether another user may clear the vault.

## Consequences

- A partial network failure resumes without re-sending locally confirmed photos.
- Server upload idempotency remains the fallback if the response arrives but
  local receipt persistence is interrupted.
- Upload does not validate the ruler, image quality, location, vegetation
  height, inspection execution, or eligibility for official reporting.
- Automated background transfer, retrieval, retention, EXIF handling, malware
  checks, and human quality review remain separate increments.
