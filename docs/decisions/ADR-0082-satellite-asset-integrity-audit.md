# ADR-0082: Satellite asset integrity audit and lineage location

- Status: accepted for the academic pilot; divergence handling still needs the data owner
- Date: 2026-09-15
- Ticket: PLANET-007
- Predecessors: ADR-0077, ADR-0078, ADR-0081

## Context

Stored provider assets carry a SHA-256 checksum verified at download time, but
nothing re-checks the bytes afterwards. Silent corruption, a replaced object or
a lost object would only surface when a later processing step produced a wrong
result.

The repository already has a `data_lineage` table, unused so far. Its
constraint requires exactly one parent among `source_file` and `import_run`,
which describe imported documents. A provider asset has neither parent: it comes
from a catalog scene and, for Planet, from an Order.

## Decision

Keep lineage where each entity already lives. `satellite_asset` links to its
scene and, through `source_order_id`, to its Planet Order; migration `0045` adds
the object version and the byte size so a verification targets exactly the bytes
that were registered. `data_lineage` stays reserved for imported source files,
and this ADR is the justification for not stretching it to provider assets.

Migration `0045` also adds `satellite_asset_verification`: an append-only audit
where each run records the expected checksum, the observed checksum, the byte
count, the verifier version and one of `verified`, `mismatch`, `missing` or
`unreadable`. Database constraints keep a `verified` record honest: it may only
exist when the observed checksum equals the expected one.

`zenit-asset-lineage --verify` reads each object, decrypts it, recomputes the
checksum and appends the audit records. It never edits or deletes an asset, and
it exits non-zero when any asset is not usable. `--export` prints a
deterministic lineage manifest, including derived artifacts declared in
repository manifests, and reads nothing from object storage.

## Consequences

- A divergence becomes recorded evidence, not an automatic correction; the data
  owner decides whether to retain, re-download or discard the asset.
- The audit history cannot be rewritten, so a later report can show when an
  asset was last proven intact.
- Assets stored before this migration keep `storage_version_id` and `size_bytes`
  null; they are still verified by checksum against the current object version.
- Re-downloading, retention enforcement and deletion of corrupted assets remain
  out of scope and depend on the approved retention policy.
- No verification result makes an asset operational or officially reportable.
- Reverting the migration is possible but deliberate: it requires
  `SET zenit.confirm_destructive = 'satellite_asset_verification'` in the same
  session, because the append-only trigger otherwise makes the table impossible
  to empty.
- A divergence in the registered size alone is still a mismatch, and the
  constraints accept it with an observed checksum equal to the expected one.
