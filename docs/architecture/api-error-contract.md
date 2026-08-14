# API error and correlation contract

## Runtime contract

Every API response includes `X-Correlation-ID`. A client may provide a canonical
UUID in that request header; the API preserves it. Missing or malformed values
are replaced with a generated UUID, so arbitrary caller input cannot enter logs
as a correlation identifier.

Every HTTP, validation, and unexpected error uses one JSON envelope:

```json
{
  "code": "request_validation_failed",
  "message": "Request validation failed",
  "details": [
    {
      "location": ["body", "password"],
      "message": "Field required",
      "type": "missing"
    }
  ],
  "correlation_id": "20000000-0000-4000-8000-000000000001"
}
```

`details` is `null` for HTTP and internal errors. Validation details contain
only location, message, and validator type; request values and bodies are not
copied into the response. Unexpected exceptions use a generic message and are
logged with the correlation identifier without returning internal details.

## Stable codes

The MVP maps common statuses to `bad_request`, `authentication_required`,
`forbidden`, `not_found`, `method_not_allowed`, `conflict`,
`payload_too_large`, `unsupported_media_type`, `unprocessable_content`,
`rate_limit_exceeded`, and `service_unavailable`. FastAPI request validation
uses `request_validation_failed`; unexpected failures use
`internal_server_error`. Other HTTP statuses use `http_<status>_error`.

Authentication challenges such as `WWW-Authenticate` remain intact. The
versioned OpenAPI contract requires the envelope and correlation response
header for both `422` and default error responses on every operation.

## Safety boundary

A correlation identifier links technical diagnostics only. It is not an actor
identity, human approval, work authorization, confidence value, data status,
lineage record, or evidence that information is eligible for model training or
official reporting.
