# ZENIT mobile

Android-first, offline-first field application scaffold for the ZENIT MVP.

Current P0 slice:

- initial online OAuth password login against the ZENIT API;
- access token stored in Android secure storage (the password is never stored);
- prepared inspection orders downloaded from `GET /v1/work-orders`;
- prepared mowing-planning snapshots downloaded from
  `GET /v1/prepared-mowing-orders` for encrypted offline review;
- order snapshot and three measurement drafts stored in an AES-256 encrypted
  Hive CE vault whose key is protected by Android secure storage;
- offline demo lifecycle (`confirm`, simulated-location `start`, and `finish`)
  persisted alongside the measurements;
- separate mowing rehearsal (`confirm`, simulated-point `start`, balanced
  `pause`/`resume`, and `finish`) persisted and synchronized without real GPS;
- exactly three post-service mowing heights captured after `finish` as separate
  simulated, unverified drafts and synchronized after the ordered lifecycle;
- one later post-service photo per measured mowing point copied into the
  encrypted vault; its simulated, unverified, `not_uploaded` manifest is
  synchronized before any bytes;
- explicit upload of accepted post-service mowing-photo manifests with
  per-photo resumable `uploaded_unverified` receipts;
- one inspection camera photo per planned point copied into the encrypted vault
  with a verified local SHA-256; only its prepared manifest enters sync;
- persistent event and batch UUIDs created before network delivery;
- authenticated device registration and idempotent prepared-batch sync;
- explicit upload of accepted inspection-photo manifests with resumable
  unverified receipts;
- accepted, rejected, and conflicting outcomes retained locally;
- logout/session expiry hides but does not delete unacknowledged encrypted data;
- Android cloud backup and device-transfer extraction disabled.

Safety boundary: every accepted order must explicitly have
`authorizes_field_work=false`, `eligible_for_field_execution=false`, and
`eligible_for_official_reporting=false`. Measurements remain `prepared` and
declare GPS/photos as not collected. The demo start uses the first estimated
planned point only as an explicitly `simulated`, `demo_only` coordinate. These
events do not mutate the prepared order or make any data operational/official.
Photo bytes remain encrypted on the device and, when explicitly uploaded, are
still prepared and unverified; their ruler presence and quality remain
unvalidated.

Mowing planning is a separate guarded demonstration surface. Candidate team
and equipment references, manual weather/safety declarations, and planning
decisions retain their provenance, but do not satisfy operational approval. An
effective snapshot with prepared `clear` weather and safety declarations can
drive only a simulated rehearsal. Its start reuses the first estimated point
from the linked prepared inspection order; the app never reads device location.
Every event is labelled `simulated`, `demo_only`, and
`mowing_demo_rehearsal_only`, and remains ineligible for execution, training,
or official reporting. Any promoted flag, broken provenance link, missing
source point, stale planning approval, or invalid sequence makes the client
fail closed.

After a valid rehearsal reaches `finish`, the app can encrypt exactly one
post-service height for each of the three source planned points. These drafts
are separate from inspection measurements and fixed to `simulated`,
`simulated_unverified`, and `mowing_demo_post_service_only`; GPS and photos are
explicitly not collected by the typed height record. A fully local rehearsal
sends its ordered lifecycle before interleaved height/manifest pairs in one
idempotent batch. A previously acknowledged rehearsal sends only new
measurements and manifests, while previously acknowledged measurements allow a
manifest-only batch. After all three manifests are accepted, a separate user
action uploads the exact encrypted-vault bytes and persists each unverified
receipt before continuing, allowing interrupted transfers to resume. None of
these paths proves vegetation condition, mowing completion, location, or image
quality. See
`docs/decisions/ADR-0036-mobile-simulated-mowing-post-service-measurements.md`
through
`docs/decisions/ADR-0041-mobile-simulated-mowing-photo-upload-orchestration.md`.

Run checks from this directory with the repository-local Flutter SDK:

```bash
../../.tools/flutter/bin/flutter --no-version-check --suppress-analytics analyze
../../.tools/flutter/bin/flutter --no-version-check --suppress-analytics test
```

The emulator default is `http://10.0.2.2:8000`. Override it without changing
source code:

```bash
../../.tools/flutter/bin/flutter run \
  --dart-define=ZENIT_API_BASE_URL=https://api.example.test \
  --dart-define=ZENIT_APP_VERSION=1.0.0+1
```

Production builds must use HTTPS. The default HTTP address is intended only for
an Android emulator connected to the local development API.
