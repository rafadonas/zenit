# ADR-0081: Planet quota control

- Status: accepted for the bounded academic pilot; budget values still need the data owner
- Date: 2026-09-15
- Ticket: PLANET-005
- Predecessors: ADR-0067, ADR-0077, ADR-0078

## Context

Planet Orders consume a shared account quota by area and delivered bytes. The
bounded Order gate limits a single request (10 000 m² and 100 MiB) but nothing
limits how many requests the project may issue, and nothing records what the
account already spent. Without that, a repeated command can exhaust the quota of
an account the project does not own.

Counting consumption in a new table would create a second source of truth that
can drift from the Orders actually created.

## Decision

Migration `0044` adds `planet_quota_budget`: an approved budget for a period,
with area, byte and Order limits, the approval reference, the approver and the
approval instant. The table is append-only through a trigger, and a GiST
exclusion constraint on `tstzrange(period_start, period_end)` guarantees that at
most one budget covers any instant, so the active budget is never ambiguous.

Consumption is **derived**, not counted separately: it is the sum of
`aoi_area_m2` and `downloaded_bytes` over the `planet_order` rows created inside
the period whose state is `queued`, `running`, `success` or `failed`. A
`cancelled` Order never reached the provider and does not consume the budget.

`zenit-planet-order` resolves the budget and calls `ensure_capacity` **before**
the catalog search and before the Order request. Without an approved budget for
the current instant, the command fails closed. `zenit-planet-quota` prints the
budget, the consumption and the remaining balance without writing anything.

Both commands take an explicit `--database-url`; the configured host is never
rewritten.

## Consequences

- An Order that would exceed the approved area, bytes or count is refused before
  any external call, with the remaining balance in the message.
- Recording a budget is an approval act: it names who approved it and cannot be
  edited afterwards, only superseded by a later period.
- A failed Order still consumes the budget, which matches how the provider
  accounts for it.
- The budget is not a licence, a cost approval or an operational authorization,
  and no value here makes a result official.
- Tile consumption is out of scope and belongs to PLANET-006.
- Reverting the migration is possible but deliberate: it requires
  `SET zenit.confirm_destructive = 'planet_quota_budget'` in the same session,
  because the append-only trigger otherwise makes the table impossible to empty.
