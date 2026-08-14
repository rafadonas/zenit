#!/usr/bin/env python3
"""Export or verify the versioned ZENIT OpenAPI contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path("contracts/openapi.json")
HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}
SENSITIVE_MARKERS = {
    "change_me",
    "development-only-change-this-authentication-secret",
    "postgresql://zenit:",
    "postgresql+psycopg://zenit:",
    "ZGV2ZWxvcG1lbnQtb25seS0zMi1ieXRlLWtleSEhISE=",
}
ERROR_RESPONSE_REF = "#/components/schemas/ApiErrorResponse"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class OpenApiContractError(RuntimeError):
    """Raised when the generated OpenAPI document violates the repository contract."""


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OpenApiContractError(f"{name} must be an object")
    return value


def validate_openapi_contract(schema: Mapping[str, Any]) -> None:
    if schema.get("openapi") != "3.1.0":
        raise OpenApiContractError("OpenAPI version must be 3.1.0")
    info = _object(schema.get("info"), "info")
    if info.get("title") != "ZENIT API" or info.get("version") != "0.1.0":
        raise OpenApiContractError("API title and version must match the MVP contract")

    components = _object(schema.get("components"), "components")
    schemas = _object(components.get("schemas"), "components.schemas")
    error_schema = _object(schemas.get("ApiErrorResponse"), "ApiErrorResponse")
    error_properties = _object(error_schema.get("properties"), "ApiErrorResponse.properties")
    required_error_fields = {"code", "message", "details", "correlation_id"}
    declared_error_fields = set(error_schema.get("required", []))
    if declared_error_fields != required_error_fields or not required_error_fields <= set(
        error_properties
    ):
        raise OpenApiContractError("ApiErrorResponse must require the stable error fields")

    correlation_property = _object(
        error_properties.get("correlation_id"),
        "ApiErrorResponse.correlation_id",
    )
    if correlation_property.get("type") != "string" or correlation_property.get("format") != "uuid":
        raise OpenApiContractError("ApiErrorResponse correlation_id must be a UUID string")

    paths = _object(schema.get("paths"), "paths")
    if "/health" not in paths:
        raise OpenApiContractError("the public /health contract is missing")
    operation_ids: set[str] = set()
    operation_count = 0
    for path, raw_path_item in paths.items():
        if not isinstance(path, str) or (path != "/health" and not path.startswith("/v1/")):
            raise OpenApiContractError(f"API path is outside the versioned contract: {path!r}")
        path_item = _object(raw_path_item, f"paths.{path}")
        for method, raw_operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            operation = _object(raw_operation, f"paths.{path}.{method}")
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise OpenApiContractError(f"{method.upper()} {path} has no operationId")
            if operation_id in operation_ids:
                raise OpenApiContractError(f"duplicate operationId: {operation_id}")
            operation_ids.add(operation_id)
            tags = operation.get("tags")
            if (
                not isinstance(tags, list)
                or not tags
                or not all(isinstance(tag, str) for tag in tags)
            ):
                raise OpenApiContractError(f"{method.upper()} {path} has no valid tags")
            responses = operation.get("responses")
            if not isinstance(responses, Mapping) or not responses:
                raise OpenApiContractError(f"{method.upper()} {path} has no responses")
            for status_code in ("422", "default"):
                error_response = _object(
                    responses.get(status_code),
                    f"paths.{path}.{method}.responses.{status_code}",
                )
                headers = _object(error_response.get("headers"), "error response headers")
                correlation_header = _object(
                    headers.get(CORRELATION_ID_HEADER),
                    f"error response {CORRELATION_ID_HEADER}",
                )
                header_schema = _object(
                    correlation_header.get("schema"),
                    f"error response {CORRELATION_ID_HEADER} schema",
                )
                if header_schema.get("type") != "string" or header_schema.get("format") != "uuid":
                    raise OpenApiContractError("error correlation header must be a UUID string")
                content = _object(error_response.get("content"), "error response content")
                json_content = _object(content.get("application/json"), "error JSON content")
                response_schema = _object(json_content.get("schema"), "error JSON schema")
                if response_schema.get("$ref") != ERROR_RESPONSE_REF:
                    raise OpenApiContractError(
                        f"{method.upper()} {path} has no stable {status_code} error response"
                    )
            operation_count += 1
    if operation_count == 0:
        raise OpenApiContractError("OpenAPI contract contains no operations")

    serialized = json.dumps(schema, sort_keys=True)
    leaked = sorted(marker for marker in SENSITIVE_MARKERS if marker in serialized)
    if leaked:
        raise OpenApiContractError("OpenAPI contract contains a development secret or credential")


def build_openapi_contract() -> Mapping[str, Any]:
    from zenit_api.main import app

    schema = app.openapi()
    validate_openapi_contract(schema)
    return schema


def render_openapi_contract() -> str:
    return json.dumps(
        build_openapi_contract(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when the tracked contract differs",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        rendered = render_openapi_contract()
        if args.check:
            if not args.output.is_file():
                raise OpenApiContractError(f"tracked OpenAPI contract is missing: {args.output}")
            tracked = args.output.read_text(encoding="utf-8")
            if tracked != rendered:
                raise OpenApiContractError(
                    "tracked OpenAPI contract is stale "
                    f"(tracked {_sha256(tracked)}, generated {_sha256(rendered)}); "
                    "run scripts/export_openapi.py"
                )
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
    except (OSError, OpenApiContractError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    path_count = len(_object(build_openapi_contract().get("paths"), "paths"))
    action = "matches" if args.check else "wrote"
    print(f"OK {action} {args.output}: {_sha256(rendered)} ({path_count} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
