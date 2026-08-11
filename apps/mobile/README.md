# ZENIT mobile

Android-first, offline-first field application scaffold for the ZENIT MVP.

Current P0 slice:

- initial online OAuth password login against the ZENIT API;
- access token stored in Android secure storage (the password is never stored);
- prepared inspection orders downloaded from `GET /v1/work-orders`;
- order snapshot and three measurement drafts stored in an AES-256 encrypted
  Hive CE vault whose key is protected by Android secure storage;
- offline demo lifecycle (`confirm`, simulated-location `start`, and `finish`)
  persisted alongside the measurements;
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
