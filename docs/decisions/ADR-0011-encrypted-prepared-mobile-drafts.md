# ADR-0011: Encrypted prepared mobile drafts

- Status: accepted
- Date: 2026-08-09

## Context

Sprint 5 starts the Android offline-first workflow, but the only available work
orders are the non-operational prepared orders established by ADR-0010. Their
centerline points use estimated/prepared geometry and cannot authorize travel,
inspection, mowing, or official reporting. The mobile device also needs to keep
an access token, downloaded order data, and draft measurements without storing
the user's password or exposing local data through Android backup.

The development workstation did not previously have a Flutter toolchain. The
repository-local SDK is intentionally ignored by Git; the application and its
locked dependencies remain reproducible in CI.

## Decision

Create an Android-first Flutter application using Flutter 3.44.9 and Dart
3.12.2. The first cohesive P0 slice provides initial online OAuth password
login and authenticated download from `GET /v1/work-orders`. Store the access
token in Android secure storage and never persist the password.

Use Hive CE for the small offline snapshot and measurement-draft workload. Open
the vault with its built-in AES-256 cipher and protect the randomly generated
32-byte vault key with Android secure storage. Disable cloud backup and device
transfer extraction. Explicit logout clears the session and encrypted user
data; an expired/missing session also removes a cached order snapshot.

Accept only API orders that explicitly assert all three non-operational flags:
`authorizes_field_work=false`, `eligible_for_field_execution=false`, and
`eligible_for_official_reporting=false`. Also require status/data status
`prepared` and exactly three ordered centerline points. Reject the payload
rather than weakening these invariants.

Allow the user to save exactly three height drafts, one per prepared point.
Label every draft `prepared`, `local_only`, and ineligible for official
reporting. This increment intentionally has no field start/finish event, GPS,
photo, sync acknowledgment, conflict resolution, background tracking, or
offline PIN/biometric unlock.

Pin direct dependency ranges and commit `pubspec.lock`. Add CI formatting,
analysis, tests, and a debug Android APK build. The local emulator may use its
debug-only cleartext connection to `10.0.2.2`; production builds do not enable
cleartext traffic and must receive an HTTPS API URL through `--dart-define`.

## Consequences

- A prepared order can be reviewed and measured as an encrypted local draft,
  but the app cannot represent this as completed field work.
- Logging out sacrifices unsynchronized drafts by design in this first slice;
  the UI states that local data will be removed.
- Hive CE fits the bounded key-value workload without a native SQLCipher fork.
  A later relational requirement may justify a separately reviewed migration.
- GPS/photo capture and idempotent event synchronization require new server
  contracts and append-only provenance tables before they can be enabled.
- Device enrollment/revocation and offline unlock remain required before a
  production pilot; secure token storage alone is not a complete device-trust
  policy.
