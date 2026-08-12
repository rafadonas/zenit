# ADR-0039: Mobile encrypted simulated mowing post-service photos

- Status: accepted
- Date: 2026-08-12

## Context

ADR-0038 created a separate server manifest for simulated post-service mowing
photos. The mobile app still captured only the three separate heights, and the
inspection-photo draft could not be reused without losing the post-service
phase, mowing-planning provenance, and simulated evidence labels.

## Decision

Capture one separate post-service image for each of the three measured source
points. Allow capture only after the matching simulated measurement exists and
require the client capture time not to precede that measurement. Copy the
JPEG/PNG bytes into the existing AES-256 Hive vault, verify their SHA-256 on
every decode, and preserve stable event and photo UUIDs across retries.

Fix every draft and sync manifest to `post_service`,
`mowing_demo_post_service_only`, `not_uploaded`, `not_validated`,
`not_collected`, `simulated`, and `simulated_unverified`. Keep operational
approval, field authorization, execution eligibility, model-training
eligibility, and official-reporting eligibility false. Never place bytes or a
base64 representation in the sync event.

When measurements are still local, order each measurement immediately before
its photo manifest in the same persistent batch. When the lifecycle and
measurements were already acknowledged, synchronize only the three new
manifests. Retain source snapshots and acknowledged encrypted bytes because no
post-service upload boundary exists yet. Prevent edits after a manifest has a
persistent accepted, rejected, or conflicting result.

## Consequences

- A fully offline rehearsal can retain its heights and images with point-level
  provenance and retry-safe identifiers.
- A persisted manifest proves only receipt of checksum-bound metadata; it does
  not prove possession, quality, ruler visibility, location, mowing, or
  vegetation condition.
- The measurement's `photo_status=not_collected` continues to mean the typed
  height record does not embed or validate an image; the later image is a
  separate evidence object.
- Verified encrypted upload, upload receipts, authorized retrieval, retention
  policy, and human review remain separate P0 increments.
