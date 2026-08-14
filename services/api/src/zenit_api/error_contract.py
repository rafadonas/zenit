"""Stable API error responses and request correlation identifiers."""

from __future__ import annotations

import logging
from http import HTTPStatus
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

CORRELATION_ID_HEADER = "X-Correlation-ID"


class ApiErrorDetail(BaseModel):
    location: list[str | int]
    message: str
    type: str


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ApiErrorDetail] | None
    correlation_id: UUID


_CORRELATION_ID_RESPONSE_HEADER = {
    "description": "Request correlation identifier generated or accepted by the API.",
    "schema": {"type": "string", "format": "uuid"},
}

API_ERROR_RESPONSES = {
    422: {
        "model": ApiErrorResponse,
        "description": "Request validation failed or the request cannot be processed.",
        "headers": {CORRELATION_ID_HEADER: _CORRELATION_ID_RESPONSE_HEADER},
    },
    "default": {
        "model": ApiErrorResponse,
        "description": "API error response.",
        "headers": {CORRELATION_ID_HEADER: _CORRELATION_ID_RESPONSE_HEADER},
    },
}

_STATUS_CODES = {
    400: "bad_request",
    401: "authentication_required",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "unprocessable_content",
    429: "rate_limit_exceeded",
    503: "service_unavailable",
}

logger = logging.getLogger(__name__)


def _normalize_correlation_id(value: str | None) -> UUID:
    if value is not None:
        try:
            parsed = UUID(value)
        except ValueError:
            pass
        else:
            if str(parsed) == value.lower():
                return parsed
    return uuid4()


def _request_correlation_id(request: Request) -> UUID:
    correlation_id = getattr(request.state, "correlation_id", None)
    if isinstance(correlation_id, UUID):
        return correlation_id

    correlation_id = _normalize_correlation_id(request.headers.get(CORRELATION_ID_HEADER))
    request.state.correlation_id = correlation_id
    return correlation_id


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ApiErrorDetail] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    correlation_id = _request_correlation_id(request)
    response_headers = dict(headers or {})
    response_headers[CORRELATION_ID_HEADER] = str(correlation_id)
    payload = ApiErrorResponse(
        code=code,
        message=message,
        details=details,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=response_headers,
    )


async def correlation_id_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    correlation_id = _request_correlation_id(request)
    response = await call_next(request)
    response.headers[CORRELATION_ID_HEADER] = str(correlation_id)
    return response


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    if isinstance(exc.detail, str):
        message = exc.detail
    else:
        try:
            message = HTTPStatus(exc.status_code).phrase
        except ValueError:
            message = "Request failed"

    return _error_response(
        request,
        status_code=exc.status_code,
        code=_STATUS_CODES.get(exc.status_code, f"http_{exc.status_code}_error"),
        message=message,
        headers=exc.headers,
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        ApiErrorDetail(
            location=[part if isinstance(part, (str, int)) else str(part) for part in error["loc"]],
            message=error["msg"],
            type=error["type"],
        )
        for error in exc.errors()
    ]
    return _error_response(
        request,
        status_code=422,
        code="request_validation_failed",
        message="Request validation failed",
        details=details,
    )


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = _request_correlation_id(request)
    logger.error(
        "Unhandled API exception",
        extra={"correlation_id": str(correlation_id)},
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return _error_response(
        request,
        status_code=500,
        code="internal_server_error",
        message="An internal server error occurred",
    )


def install_error_contract(app: FastAPI) -> None:
    app.middleware("http")(correlation_id_middleware)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, internal_server_error_handler)
