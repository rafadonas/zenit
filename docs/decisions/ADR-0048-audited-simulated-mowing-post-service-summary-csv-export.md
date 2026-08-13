# ADR-0048: Audited simulated mowing post-service summary CSV export

- Status: accepted
- Date: 2026-08-13

## Decision

Provide a CSV export for simulated mowing post-service summaries with an
append-only export event, checksum, byte size, schema version, actor, purpose,
and idempotency key. The export is labeled
`simulated-mowing-post-service-summary-csv-v1`, `post_service`,
`mowing_demo_post_service_only`, `not_collected`, and `simulated`.

The CSV contains only the already persisted summary aggregates and safety
labels. Spreadsheet formula prefixes in free-text fields are neutralized. The
dashboard proxy verifies content type, checksum, schema version, simulated
status, location status, official-reporting block, and field-authorization
block before returning the file.

This is not an official report, field evidence, execution proof, mowing
completion, model-training input, or map/history update.
