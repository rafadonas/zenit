"""Secure HTTP and OAuth support for satellite catalog integrations."""

from __future__ import annotations

import json
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from zenit_geospatial.satellite_providers import (
    CBERS_STAC_URL,
    SENTINEL_CATALOG_URL,
    CbersStacProvider,
    SearchPage,
    SentinelCatalogProvider,
)

COPERNICUS_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/"
    "protocol/openid-connect/token"
)


class SatelliteHttpError(RuntimeError):
    """Sanitized provider error that never includes response bodies or credentials."""

    def __init__(self, status_code: int | None, retryable: bool) -> None:
        label = str(status_code) if status_code is not None else "network"
        super().__init__(f"satellite provider request failed ({label})")
        self.status_code = status_code
        self.retryable = retryable


class SatelliteAuthenticationError(RuntimeError):
    """Sanitized OAuth configuration or response error."""


class JsonTransport(Protocol):
    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]: ...

    def post_form(
        self,
        url: str,
        payload: Mapping[str, str],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 0.25
    maximum_delay_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.base_delay_seconds < 0 or self.maximum_delay_seconds < 0:
            raise ValueError("retry delays cannot be negative")


@dataclass(frozen=True, slots=True)
class BinaryResponse:
    body: bytes
    content_type: str


class UrllibJsonTransport:
    """Small standard-library transport with bounded transient retries."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        retry_policy: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._retry_policy = retry_policy or RetryPolicy()
        self._sleep = sleep
        self._jitter = jitter

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return self._post(url, body, "application/json", headers)

    def post_form(
        self,
        url: str,
        payload: Mapping[str, str],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        body = urllib.parse.urlencode(payload).encode("utf-8")
        return self._post(url, body, "application/x-www-form-urlencoded", headers)

    def post_bytes(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> BinaryResponse:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        response_body, content_type = self._post_raw(url, body, "application/json", headers)
        return BinaryResponse(body=response_body, content_type=content_type)

    def _post(
        self,
        url: str,
        body: bytes,
        content_type: str,
        headers: Mapping[str, str] | None,
    ) -> Mapping[str, Any]:
        response_body, _ = self._post_raw(url, body, content_type, headers)
        return _decode_json_object(response_body)

    def _post_raw(
        self,
        url: str,
        body: bytes,
        content_type: str,
        headers: Mapping[str, str] | None,
    ) -> tuple[bytes, str]:
        request_headers = {"Content-Type": content_type}
        request_headers.update(headers or {})
        request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")

        for attempt in range(self._retry_policy.max_attempts):
            try:
                with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                    return response.read(), response.headers.get("Content-Type", "")
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or 500 <= error.code < 600
                if not retryable or attempt + 1 >= self._retry_policy.max_attempts:
                    raise SatelliteHttpError(error.code, retryable) from error
                self._sleep(self._retry_delay(attempt, error.headers.get("Retry-After")))
            except (TimeoutError, urllib.error.URLError) as error:
                if attempt + 1 >= self._retry_policy.max_attempts:
                    raise SatelliteHttpError(None, True) from error
                self._sleep(self._retry_delay(attempt, None))
        raise AssertionError("retry loop exited unexpectedly")

    def _retry_delay(self, attempt: int, retry_after: str | None) -> float:
        server_delay = 0.0
        if retry_after:
            try:
                # Sentinel Hub documents Retry-After in milliseconds.
                server_delay = max(0.0, float(retry_after) / 1000.0)
            except ValueError:
                server_delay = 0.0
        exponential = self._retry_policy.base_delay_seconds * (2**attempt)
        delay = max(server_delay, exponential) + self._jitter() * 0.1
        return min(delay, self._retry_policy.maximum_delay_seconds)


def _decode_json_object(body: bytes) -> Mapping[str, Any]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SatelliteHttpError(None, False) from error
    if not isinstance(payload, dict):
        raise SatelliteHttpError(None, False)
    return payload


class CopernicusTokenProvider:
    """Thread-safe client-credentials token cache with early renewal."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        transport: JsonTransport,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        renewal_margin_seconds: float = 60.0,
    ) -> None:
        if not client_id or not client_secret:
            raise SatelliteAuthenticationError("Copernicus OAuth credentials are not configured")
        self._client_id = client_id
        self._client_secret = client_secret
        self._transport = transport
        self._monotonic = monotonic
        self._renewal_margin_seconds = renewal_margin_seconds
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        now = self._monotonic()
        if self._access_token is not None and now < self._expires_at:
            return self._access_token
        with self._lock:
            now = self._monotonic()
            if self._access_token is not None and now < self._expires_at:
                return self._access_token
            payload = self._transport.post_form(
                COPERNICUS_TOKEN_URL,
                {
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            token = payload.get("access_token")
            expires_in = payload.get("expires_in")
            if not isinstance(token, str) or not token:
                raise SatelliteAuthenticationError("Copernicus token response has no access token")
            if not isinstance(expires_in, (int, float)) or expires_in <= 0:
                raise SatelliteAuthenticationError("Copernicus token response has invalid expiry")
            usable_seconds = max(1.0, float(expires_in) - self._renewal_margin_seconds)
            self._access_token = token
            self._expires_at = now + usable_seconds
            return token


class SentinelCatalogClient:
    def __init__(self, transport: JsonTransport, token_provider: CopernicusTokenProvider) -> None:
        self._transport = transport
        self._token_provider = token_provider
        self._provider = SentinelCatalogProvider()

    def search(self, payload: Mapping[str, Any]) -> SearchPage:
        response = self._transport.post_json(
            SENTINEL_CATALOG_URL,
            payload,
            headers={"Authorization": f"Bearer {self._token_provider.get_token()}"},
        )
        return self._provider.parse_search_page(response)


class CbersCatalogClient:
    def __init__(self, transport: JsonTransport, provider: CbersStacProvider | None = None) -> None:
        self._transport = transport
        self._provider = provider or CbersStacProvider()

    def search(self, payload: Mapping[str, Any], access_token: str | None = None) -> SearchPage:
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else None
        response = self._transport.post_json(CBERS_STAC_URL, payload, headers=headers)
        return self._provider.parse_search_page(response)
