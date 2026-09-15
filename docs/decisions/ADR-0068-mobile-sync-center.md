# ADR-0068: Actionable mobile synchronization center

- Status: accepted
- Date: 2026-09-14

## Context

The mobile client already preserves prepared inspection and simulated mowing
events across transport failure, process restart, and logout. Each feature page
can initiate synchronization, but the user has no single place to understand
pending work, persistent outcomes, retry attempts, or the manifest-before-bytes
dependency.

## Decision

Add an authenticated, read-only projection of the encrypted local evidence queue.
Derive pending, accepted, rejected, and conflict states from the existing drafts,
events, manifests, and upload receipts. Show `sending` only as transient UI state.

Persist an attempt counter and last-attempt timestamp in the existing encrypted
Hive vault before each user-triggered batch or media-upload attempt. Attempt
metadata never replaces evidence and is cleared only with the same guarded user
data cleanup as the rest of the vault.

Retry through the existing feature operations so persisted batch and event UUIDs
remain unchanged. Enable byte upload only after all three matching manifests have
persistent acknowledgement. Rejected and conflicting evidence remains immutable;
the center explains that it must be reviewed instead of offering overwrite.

Bound every mobile API request with a configurable timeout. The tracked
demonstration default is 30 seconds and is not an approved operational or Motiva
value. A timeout becomes a stable retryable client error while the encrypted
pending batch, session, evidence, and identifiers remain intact. An HTTP 409 also
retains the pending batch and session, surfaces the server conflict message, and
any retry continues to use the exact persisted identifiers.

Do not add background synchronization, connectivity scheduling, a new dependency,
an API field, or an operational eligibility transition.

## Consequences

- A field user can see all locally known synchronization work and resume eligible
  retries after transport failure or process restart.
- Attempt counts survive restart without becoming evidence of field execution.
- Partial uploads resume through the existing per-photo receipts.
- A stored attempt does not prove server receipt; only persistent event outcomes
  and upload receipts do.
- Prepared and simulated data remains ineligible for field execution, model
  training, and official reporting.
