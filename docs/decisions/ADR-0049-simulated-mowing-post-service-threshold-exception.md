# ADR-0049: Simulated mowing post-service threshold exception

- Status: accepted
- Date: 2026-08-13

## Decision

Create an append-only simulated post-service exception assessment from a
generated mowing post-service summary. The rule uses 30 cm as the general
threshold and 10 cm for special zones. If the maximum typed post-service height
still exceeds the applicable threshold, the recommendation is
`inspect_follow_up`; otherwise it is `monitor`.

The assessment is `post_service`, `simulated`, `not_collected`, requires human
review, and keeps model training, official reporting, and field authorization
false. It never creates a mowing order, completion claim, map update, official
history update, or automatic field action.
