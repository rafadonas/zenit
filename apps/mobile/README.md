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
- one camera photo per planned point copied into the encrypted vault with a
  verified local SHA-256; only its prepared manifest enters sync;
- persistent event and batch UUIDs created before network delivery;
- authenticated device registration and idempotent prepared-batch sync;
- explicit upload of accepted photo manifests with resumable unverified receipts;
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
