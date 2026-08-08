import io
import unittest
import urllib.error
from collections.abc import Mapping
from typing import Any
from unittest.mock import patch

from zenit_geospatial.satellite_http import (
    COPERNICUS_TOKEN_URL,
    CopernicusTokenProvider,
    RetryPolicy,
    SatelliteAuthenticationError,
    SatelliteHttpError,
    SentinelCatalogClient,
    UrllibJsonTransport,
)
from zenit_geospatial.satellite_providers import SENTINEL_CATALOG_URL


class FakeTransport:
    def __init__(self) -> None:
        self.form_calls: list[tuple[str, Mapping[str, str]]] = []
        self.json_calls: list[tuple[str, Mapping[str, Any], Mapping[str, str] | None]] = []

    def post_form(
        self,
        url: str,
        payload: Mapping[str, str],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        self.form_calls.append((url, payload))
        return {"access_token": "private-token", "expires_in": 300}

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        self.json_calls.append((url, payload, headers))
        return {"features": []}


class SatelliteHttpTests(unittest.TestCase):
    def test_token_is_cached_and_renewed_before_expiry(self) -> None:
        transport = FakeTransport()
        clock = [100.0]
        provider = CopernicusTokenProvider(
            "client-id",
            "client-secret",
            transport,
            monotonic=lambda: clock[0],
            renewal_margin_seconds=60,
        )

        self.assertEqual(provider.get_token(), "private-token")
        self.assertEqual(provider.get_token(), "private-token")
        self.assertEqual(len(transport.form_calls), 1)
        self.assertEqual(transport.form_calls[0][0], COPERNICUS_TOKEN_URL)

        clock[0] = 341.0
        self.assertEqual(provider.get_token(), "private-token")
        self.assertEqual(len(transport.form_calls), 2)

    def test_empty_credentials_fail_without_a_request(self) -> None:
        with self.assertRaisesRegex(SatelliteAuthenticationError, "not configured"):
            CopernicusTokenProvider("", "", FakeTransport())

    def test_catalog_client_adds_bearer_token_without_changing_payload(self) -> None:
        transport = FakeTransport()
        token_provider = CopernicusTokenProvider("id", "secret", transport)
        request = {"collections": ["sentinel-2-l2a"], "limit": 1}

        page = SentinelCatalogClient(transport, token_provider).search(request)

        self.assertEqual(page.acquisitions, ())
        url, payload, headers = transport.json_calls[0]
        self.assertEqual(url, SENTINEL_CATALOG_URL)
        self.assertEqual(payload, request)
        self.assertEqual(headers, {"Authorization": "Bearer private-token"})

    def test_transport_retries_429_without_exposing_response_body(self) -> None:
        attempts = []
        response = io.BytesIO(b'{"features": []}')
        response.__enter__ = lambda value: value  # type: ignore[attr-defined]
        response.__exit__ = lambda *_: None  # type: ignore[attr-defined]
        response.headers = {}  # type: ignore[attr-defined]
        error = urllib.error.HTTPError(
            "https://provider.invalid",
            429,
            "rate limited",
            {"Retry-After": "250"},
            io.BytesIO(b'{"secret":"must-not-leak"}'),
        )
        outcomes = [error, response]

        def fake_urlopen(*_args, **_kwargs):
            attempts.append(1)
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        delays: list[float] = []
        transport = UrllibJsonTransport(
            retry_policy=RetryPolicy(max_attempts=2),
            sleep=delays.append,
            jitter=lambda: 0,
        )
        with patch("urllib.request.urlopen", fake_urlopen):
            payload = transport.post_json("https://provider.invalid", {})

        self.assertEqual(payload, {"features": []})
        self.assertEqual(len(attempts), 2)
        self.assertEqual(delays, [0.25])

    def test_transport_error_message_is_sanitized(self) -> None:
        error = urllib.error.HTTPError(
            "https://provider.invalid",
            401,
            "unauthorized",
            {},
            io.BytesIO(b'{"access_token":"must-not-leak"}'),
        )
        transport = UrllibJsonTransport(retry_policy=RetryPolicy(max_attempts=1))
        with (
            patch("urllib.request.urlopen", side_effect=error),
            self.assertRaises(SatelliteHttpError) as raised,
        ):
            transport.post_json("https://provider.invalid", {})

        self.assertEqual(str(raised.exception), "satellite provider request failed (401)")
        self.assertNotIn("access_token", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
