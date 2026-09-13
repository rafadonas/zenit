# ADR-0052: Validated Android demonstration release evidence

- Status: accepted
- Date: 2026-08-14

## Decision

Track a versioned JSON manifest for the ignored Android demonstration APK and
validate it with a dependency-free repository tool. The version 1 contract is
strict: unknown or duplicate keys, malformed digests, mismatched source and
verifier revisions, non-reserved API endpoints, and any operational eligibility
flag cause validation to fail.

CI validates the tracked manifest without requiring the large APK. A local
release audit supplies the ignored binary separately and verifies that its byte
size and SHA-256 match the tracked evidence. APK structure, package metadata,
Flutter ABIs, configured endpoint, and Android signature remain the
responsibility of `scripts/verify_android_apk.py`.

### Signer output compatibility (2026-09-09)

The verifier accepts the numbered `Signer #1` certificate labels and the
SDK-range labels emitted by `apksigner` for v3.1 signatures. These formats are
documented in the [Android signer tool source](https://android.googlesource.com/platform/tools/apksig/+/master/src/apksigner/java/com/android/apksigner/ApkSignerTool.java).
The debug certificate's three DN attributes may appear in either order.
Source-stamp certificates are separate and cannot satisfy the APK signer check.

Successful cryptographic verification, signature scheme v2, and exactly one
signer remain mandatory. Every reported signer range must contain a complete
debug DN and the same valid SHA-256 certificate digest. Missing or repeated
fields, mixed label formats, unexpected identities, and distinct certificates
across ranges are rejected. The evidence schema and operational restrictions
remain unchanged.

## Consequences

The repository can detect unsafe or malformed evidence changes independently
of the generated artifact, while an evaluator with the binary can bind it back
to the checked-in record. This does not make the debug APK reproducible,
operational, field-eligible, suitable for official reporting, or suitable for
model training. The APK remains ignored and release signing remains outside the
demonstration scope.
