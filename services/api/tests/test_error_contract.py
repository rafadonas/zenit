import asyncio
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from zenit_api.error_contract import (
    API_ERROR_RESPONSES,
    CORRELATION_ID_HEADER,
    install_error_contract,
)
from zenit_api.main import app


def _request(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: dict[str, str] | None = None,
):
    async def send_request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, headers=headers, data=data)

    return asyncio.run(send_request())


def test_success_response_includes_a_generated_correlation_id() -> None:
    response = _request("/openapi.json")

    assert response.status_code == 200
    assert UUID(response.headers[CORRELATION_ID_HEADER])


def test_valid_incoming_correlation_id_is_preserved() -> None:
    correlation_id = "20000000-0000-4000-8000-000000000001"

    response = _request("/openapi.json", headers={CORRELATION_ID_HEADER: correlation_id})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == correlation_id


def test_invalid_incoming_correlation_id_is_replaced() -> None:
    response = _request("/openapi.json", headers={CORRELATION_ID_HEADER: "not-a-uuid"})

    assert response.status_code == 200
    generated = response.headers[CORRELATION_ID_HEADER]
    assert generated != "not-a-uuid"
    assert UUID(generated)


def test_http_exception_uses_stable_envelope_and_preserves_auth_header() -> None:
    correlation_id = "20000000-0000-4000-8000-000000000002"

    response = _request(
        "/v1/auth/me",
        headers={CORRELATION_ID_HEADER: correlation_id},
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "authentication_required",
        "message": "Not authenticated",
        "details": None,
        "correlation_id": correlation_id,
    }
    assert response.headers[CORRELATION_ID_HEADER] == correlation_id
    assert response.headers["www-authenticate"] == "Bearer"


def test_request_validation_exposes_only_sanitized_error_details() -> None:
    response = _request(
        "/v1/auth/token",
        method="POST",
        data={"username": "manager@example.test"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "request_validation_failed"
    assert payload["message"] == "Request validation failed"
    assert payload["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    assert payload["details"] == [
        {
            "location": ["body", "password"],
            "message": "Field required",
            "type": "missing",
        }
    ]
    assert "manager@example.test" not in response.text


def test_unhandled_exception_returns_generic_error_without_leaking_details() -> None:
    test_app = FastAPI(responses=API_ERROR_RESPONSES)
    install_error_contract(test_app)

    @test_app.get("/explode")
    async def explode() -> None:
        raise RuntimeError("sensitive internal detail")

    async def send_request():
        transport = ASGITransport(app=test_app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/explode")

    response = asyncio.run(send_request())

    assert response.status_code == 500
    payload = response.json()
    assert payload["code"] == "internal_server_error"
    assert payload["message"] == "An internal server error occurred"
    assert payload["details"] is None
    assert payload["correlation_id"] == response.headers[CORRELATION_ID_HEADER]
    assert "sensitive internal detail" not in response.text


def test_openapi_documents_the_error_envelope_and_correlation_header() -> None:
    schema = app.openapi()
    schemas = schema["components"]["schemas"]
    responses = schema["paths"]["/v1/auth/token"]["post"]["responses"]

    assert "ApiErrorResponse" in schemas
    assert "ApiErrorDetail" in schemas
    assert "HTTPValidationError" not in schemas
    assert responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ApiErrorResponse"
    }
    assert responses["default"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ApiErrorResponse"
    }
    assert responses["429"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ApiErrorResponse"
    }
    assert responses["429"]["headers"]["Retry-After"]["schema"] == {
        "type": "integer",
        "minimum": 1,
    }
    assert responses["422"]["headers"][CORRELATION_ID_HEADER]["schema"] == {
        "type": "string",
        "format": "uuid",
    }
