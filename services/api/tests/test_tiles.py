import asyncio
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import Settings, get_settings
from zenit_api.main import app
from zenit_api.tiles import (
    InMemoryTileCache,
    PerUserRateLimiter,
    TileUnavailableError,
    get_tile_cache,
    get_tile_rate_limiter,
    get_tile_upstream,
)

TILE = b"\x89PNG\r\n\x1a\nfake-tile"
USER = AuthenticatedUser(
    id=UUID("60000000-0000-4000-8000-000000000001"),
    email="manager@example.test",
    display_name="Manager",
)


def settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "TILE_PROXY_ENABLED": True,
        "TILE_PROXY_ATTRIBUTION": "© Planet Labs PBC",
        "TILE_PROXY_RATE_LIMIT_PER_MINUTE": 60,
        "TILE_PROXY_CACHE_TTL_SECONDS": 3600,
    }
    values.update(overrides)
    return Settings(**values)


class FakeUpstream:
    def __init__(self, content: bytes | Exception = TILE) -> None:
        self.content = content
        self.calls: list[tuple[str, int, int, int]] = []

    def fetch(self, provider: str, z: int, x: int, y: int) -> bytes:
        self.calls.append((provider, z, x, y))
        if isinstance(self.content, Exception):
            raise self.content
        return self.content


class Harness:
    def __init__(self, *, user=USER, upstream=None, cache=None, limiter=None, **setting_overrides):
        self.upstream = upstream or FakeUpstream()
        self.cache = cache or InMemoryTileCache()
        self.limiter = limiter or PerUserRateLimiter()
        self.settings = settings(**setting_overrides)
        self.user = user

    def __enter__(self) -> "Harness":
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_tile_cache] = lambda: self.cache
        app.dependency_overrides[get_tile_rate_limiter] = lambda: self.limiter
        app.dependency_overrides[get_tile_upstream] = lambda: self.upstream
        if self.user is not None:
            app.dependency_overrides[get_current_user] = lambda: self.user
        return self

    def __exit__(self, *exc) -> None:
        app.dependency_overrides.clear()

    def get(self, path: str = "/v1/tiles/planet/12/1000/2000.png"):
        async def call():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(path)

        return asyncio.run(call())


def test_tile_proxy_is_closed_by_default() -> None:
    assert Settings(_env_file=None).tile_proxy_enabled is False

    with Harness(TILE_PROXY_ENABLED=False) as harness:
        response = harness.get()

    assert response.status_code == 404
    assert harness.upstream.calls == []


def test_enabled_proxy_serves_the_tile_with_attribution() -> None:
    with Harness() as harness:
        response = harness.get()

    assert response.status_code == 200
    assert response.content == TILE
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-tile-attribution"] == "© Planet Labs PBC"
    assert response.headers["x-tile-cache"] == "miss"
    assert response.headers["cache-control"] == "private, max-age=3600"


def test_second_request_is_served_from_cache() -> None:
    with Harness() as harness:
        first = harness.get()
        second = harness.get()

    assert first.headers["x-tile-cache"] == "miss"
    assert second.headers["x-tile-cache"] == "hit"
    assert harness.upstream.calls == [("planet", 12, 1000, 2000)]


def test_expired_cache_entry_is_refetched() -> None:
    now = [0.0]
    cache = InMemoryTileCache(clock=lambda: now[0])

    with Harness(cache=cache) as harness:
        first = harness.get()
        now[0] = 7200.0  # older than the one hour TTL
        second = harness.get()

    assert first.headers["x-tile-cache"] == "miss"
    assert second.headers["x-tile-cache"] == "miss"
    assert len(harness.upstream.calls) == 2


def test_missing_attribution_keeps_the_route_closed() -> None:
    with Harness(TILE_PROXY_ATTRIBUTION=None) as harness:
        response = harness.get()

    assert response.status_code == 404
    assert harness.upstream.calls == []


def test_unknown_provider_is_not_proxied() -> None:
    with Harness() as harness:
        response = harness.get("/v1/tiles/openstreetmap/12/1000/2000.png")

    assert response.status_code == 404
    assert harness.upstream.calls == []


def test_out_of_range_coordinates_are_rejected() -> None:
    with Harness() as harness:
        zoom = harness.get("/v1/tiles/planet/31/1/1.png")
        coordinate = harness.get("/v1/tiles/planet/2/9/1.png")

    assert zoom.status_code == 400
    assert coordinate.status_code == 400
    assert harness.upstream.calls == []


def test_rate_limit_is_per_user_and_returns_retry_after() -> None:
    with Harness(TILE_PROXY_RATE_LIMIT_PER_MINUTE=2) as harness:
        first = harness.get("/v1/tiles/planet/12/1/1.png")
        second = harness.get("/v1/tiles/planet/12/2/2.png")
        third = harness.get("/v1/tiles/planet/12/3/3.png")

    assert (first.status_code, second.status_code) == (200, 200)
    assert third.status_code == 429
    assert third.headers["retry-after"] == "60"
    assert len(harness.upstream.calls) == 2


def test_another_user_has_its_own_budget() -> None:
    limiter = PerUserRateLimiter()
    other = AuthenticatedUser(id=uuid4(), email="other@example.test", display_name="Other")

    with Harness(limiter=limiter, TILE_PROXY_RATE_LIMIT_PER_MINUTE=1) as harness:
        harness.get("/v1/tiles/planet/12/1/1.png")
        blocked = harness.get("/v1/tiles/planet/12/2/2.png")
    with Harness(limiter=limiter, user=other, TILE_PROXY_RATE_LIMIT_PER_MINUTE=1) as harness:
        allowed = harness.get("/v1/tiles/planet/12/3/3.png")

    assert blocked.status_code == 429
    assert allowed.status_code == 200


def test_upstream_failure_becomes_service_unavailable() -> None:
    with Harness(upstream=FakeUpstream(TileUnavailableError("provider down"))) as harness:
        response = harness.get()

    assert response.status_code == 503
    assert "provider down" not in response.text


def test_anonymous_request_is_rejected() -> None:
    harness = Harness()
    app.dependency_overrides[get_settings] = lambda: harness.settings
    app.dependency_overrides[get_tile_cache] = lambda: harness.cache
    app.dependency_overrides[get_tile_rate_limiter] = lambda: harness.limiter
    app.dependency_overrides[get_tile_upstream] = lambda: harness.upstream
    try:
        response = harness.get()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert harness.upstream.calls == []


def test_response_never_exposes_the_provider_key() -> None:
    with Harness() as harness:
        response = harness.get()

    body_and_headers = response.text + str(dict(response.headers))
    assert "PL_API_KEY" not in body_and_headers
    assert "api_key" not in body_and_headers.lower()


def test_upstream_url_fills_only_declared_placeholders() -> None:
    from zenit_api.tiles import build_upstream_url

    url = build_upstream_url(
        "https://tiles.example/{provider}/{z}/{x}/{y}.png", "planet", 12, 1000, 2000
    )

    assert url == "https://tiles.example/planet/12/1000/2000.png"


def test_upstream_template_must_use_https() -> None:
    from zenit_api.tiles import build_upstream_url

    try:
        build_upstream_url("http://tiles.example/{z}/{x}/{y}.png", "planet", 1, 0, 0)
    except TileUnavailableError as error:
        assert "HTTPS" in str(error)
    else:
        raise AssertionError("an insecure template was accepted")


def test_unconfigured_upstream_resolves_to_none_instead_of_raising() -> None:
    from zenit_api.tiles import get_tile_upstream as build

    assert build(settings(TILE_PROXY_UPSTREAM_TEMPLATE=None)) is None
    assert build(settings(TILE_PROXY_UPSTREAM_TEMPLATE="https://t/{z}/{x}/{y}.png")) is not None


def test_disabled_proxy_answers_404_without_an_upstream_configured() -> None:
    # The upstream dependency runs before the handler: it must not turn a closed
    # route into a 500.
    app.dependency_overrides[get_settings] = lambda: settings(
        TILE_PROXY_ENABLED=False, TILE_PROXY_UPSTREAM_TEMPLATE=None
    )
    app.dependency_overrides[get_current_user] = lambda: USER
    try:
        response = Harness().get()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_enabled_proxy_without_upstream_is_unavailable_not_broken() -> None:
    app.dependency_overrides[get_settings] = lambda: settings(TILE_PROXY_UPSTREAM_TEMPLATE=None)
    app.dependency_overrides[get_current_user] = lambda: USER
    app.dependency_overrides[get_tile_cache] = lambda: InMemoryTileCache()
    app.dependency_overrides[get_tile_rate_limiter] = lambda: PerUserRateLimiter()
    try:
        response = Harness().get()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


def test_blank_environment_values_are_treated_as_absent() -> None:
    # Compose passes empty strings for unset variables; they must not look configured.
    blank = Settings(
        _env_file=None,
        PL_API_KEY="",
        TILE_PROXY_UPSTREAM_TEMPLATE="",
        TILE_PROXY_ATTRIBUTION="   ",
    )

    assert blank.planet_api_key is None
    assert blank.tile_proxy_upstream_template is None
    assert blank.tile_proxy_attribution is None
