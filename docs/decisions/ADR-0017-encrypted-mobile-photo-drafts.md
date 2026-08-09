# ADR-0017: Encrypted mobile photo drafts

- Status: accepted
- Date: 2026-08-09

## Context

ADR-0016 created a safe server manifest but the mobile demo still lacked point
photos. Camera output initially resides in picker-managed temporary storage and
must not be treated as uploaded, validated, or official evidence.

## Decision

Use the maintained Flutter `image_picker` package for Android camera capture
and `crypto` for SHA-256. Compress camera output to quality 85 with a 2048-pixel
maximum width, accept only JPEG/PNG signatures, and cap content at 25 MiB. Copy
the bytes immediately into the existing AES-256 Hive vault, verify the checksum
when reading them back, and attempt deletion of the picker temporary file.

Require one local photo for each of the three planned points before finish.
Prepare a nine-event ordered batch: confirm, simulated start, three pairs of
measurement/photo manifest, and finish. Never include photo bytes in sync.
Persist accepted/rejected/conflicting manifest outcomes while retaining the
encrypted local content. Add a database guard and server validation requiring
three distinct manifests before finish.

## Consequences

- The demo captures real image bytes while truthfully reporting them as local,
  not uploaded, not quality-validated, and non-official.
- A manifest checksum identifies local content but does not prove server
  possession.
- Picker cleanup is best effort when Android returns a content URI managed by
  the operating system.
- Object upload, server-side checksum verification, object versioning,
  retention controls, ruler validation, and lost-capture recovery remain
  required before a field pilot.
