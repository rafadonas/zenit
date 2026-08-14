# ADR-0056: API error and correlation contract

- Status: accepted
- Date: 2026-08-14

## Decision

Return one typed error envelope containing `code`, `message`, `details`, and
`correlation_id` from HTTP, request-validation, and unexpected API failures.
Add `X-Correlation-ID` to every response, preserve canonical client UUIDs, and
replace missing or malformed values with generated UUIDs.

Keep domain endpoints raising standard FastAPI HTTP exceptions. Central
handlers translate them without discarding protocol headers, sanitize
validation details, and prevent unexpected exception text from reaching the
client. Declare the envelope as the global `422` and default response through
FastAPI so the runtime model and generated OpenAPI remain the same contract.
The OpenAPI validator enforces that contract on every operation.

## Consequences

Dashboard, mobile, integration, and support workflows receive predictable
machine-readable errors and a bounded identifier for matching server-side
diagnostics. Existing successful response bodies and domain status codes do not
change.

Correlation identifiers remain technical metadata. They do not replace audit
events, actor identity, provenance, rule/model versions, human approval, or the
eligibility gates for operations, training, and official reporting. Distributed
trace propagation and production log aggregation remain deployment work.
