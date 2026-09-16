"""PLANET-006: authenticated tile proxy with a bounded local cache.

The provider key never leaves the backend and the viewer never talks to the
provider, so the provider never sees the viewer's address. The route is closed
unless the licence rows L3/L6 of the licence register and decision D6 of the
privacy baseline are approved and the deployment enables it explicitly.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import Settings, get_settings

ALLOWED_PROVIDERS = ("planet",)
MAX_ZOOM = 20
TILE_MEDIA_TYPE = "image/png"


class TileUnavailableError(RuntimeError):
    """Raised when the upstream provider cannot serve the tile."""


class TileUpstream(Protocol):
    def fetch(self, provider: str, z: int, x: int, y: int) -> bytes: ...


class TileCache(Protocol):
    def get(self, key: str, *, max_age_seconds: int) -> bytes | None: ...

    def put(self, key: str, content: bytes) -> None: ...


class InMemoryTileCache:
    """Bounded per-process cache.

    A process restart empties it and several workers keep separate copies; that
    is acceptable for the academic, low-volume demonstration and is recorded as
    a limitation in the PLANET-006 document.
    """

    def __init__(self, *, max_entries: int = 512, clock: Callable[[], float] = time.monotonic):
        self._entries: dict[str, tuple[float, bytes]] = {}
        self._max_entries = max_entries
        self._clock = clock

    def get(self, key: str, *, max_age_seconds: int) -> bytes | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        stored_at, content = entry
        if self._clock() - stored_at > max_age_seconds:
            del self._entries[key]
            return None
        return content

    def put(self, key: str, content: bytes) -> None:
        if len(self._entries) >= self._max_entries:
            oldest = min(self._entries, key=lambda item: self._entries[item][0])
            del self._entries[oldest]
        self._entries[key] = (self._clock(), content)


class PerUserRateLimiter:
    """Sliding window per authenticated user, never per address."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._hits: dict[UUID, deque[float]] = defaultdict(deque)
        self._clock = clock

    def allow(self, user_id: UUID, *, limit_per_minute: int) -> bool:
        now = self._clock()
        hits = self._hits[user_id]
        while hits and now - hits[0] >= 60:
            hits.popleft()
        if len(hits) >= limit_per_minute:
            return False
        hits.append(now)
        return True


_CACHE = InMemoryTileCache()
_LIMITER = PerUserRateLimiter()


def get_tile_cache() -> TileCache:
    return _CACHE


def get_tile_rate_limiter() -> PerUserRateLimiter:
    return _LIMITER


def build_upstream_url(template: str, provider: str, z: int, x: int, y: int) -> str:
    """Fill only the placeholders the template declares; never echo user input elsewhere."""
    if not template.startswith("https://"):
        raise TileUnavailableError("tile upstream template must use HTTPS")
    return template.format(provider=provider, z=z, x=x, y=y)


class HttpTileUpstream:
    """Server-side fetch: the provider key stays in this process."""

    def __init__(self, template: str, api_key: str | None, *, timeout_seconds: float = 10.0):
        self._template = template
        self._api_key = api_key
        self._timeout = timeout_seconds

    def fetch(self, provider: str, z: int, x: int, y: int) -> bytes:
        request = urllib.request.Request(build_upstream_url(self._template, provider, z, x, y))
        if self._api_key:
            request.add_header("Authorization", f"api-key {self._api_key}")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                if response.status != 200:
                    raise TileUnavailableError(f"provider returned status {response.status}")
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            raise TileUnavailableError(f"provider request failed: {error}") from None


def get_tile_upstream(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TileUpstream | None:
    """Resolved for every request, so it must not raise while the proxy is closed."""
    if not settings.tile_proxy_upstream_template:
        return None
    return HttpTileUpstream(
        settings.tile_proxy_upstream_template,
        settings.planet_api_key.get_secret_value() if settings.planet_api_key else None,
    )


def _tile_disabled() -> HTTPException:
    # Fail closed and stay silent about why: the route simply does not exist yet.
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


def validate_tile_coordinates(z: int, x: int, y: int) -> None:
    if not 0 <= z <= MAX_ZOOM:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tile zoom")
    bound = 2**z
    if not (0 <= x < bound and 0 <= y < bound):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tile coordinates"
        )


router = APIRouter(prefix="/v1/tiles", tags=["tiles"])


@router.get(
    "/{provider}/{z}/{x}/{y}.png",
    response_class=Response,
    responses={
        200: {"content": {TILE_MEDIA_TYPE: {}}, "description": "Cached or proxied tile"},
        404: {"description": "Tile proxying is disabled or the provider is unknown"},
        429: {"description": "The authenticated user exceeded the tile rate limit"},
        503: {"description": "The provider could not serve the tile"},
    },
)
async def proxy_tile(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    cache: Annotated[TileCache, Depends(get_tile_cache)],
    limiter: Annotated[PerUserRateLimiter, Depends(get_tile_rate_limiter)],
    upstream: Annotated[TileUpstream | None, Depends(get_tile_upstream)],
    provider: Annotated[str, Path(max_length=32)],
    z: int,
    x: int,
    y: int,
) -> Response:
    if not settings.tile_proxy_enabled:
        raise _tile_disabled()
    if provider not in ALLOWED_PROVIDERS:
        raise _tile_disabled()
    if not settings.tile_proxy_attribution:
        # Serving without the provider attribution would breach the usage terms.
        raise _tile_disabled()
    validate_tile_coordinates(z, x, y)
    if not limiter.allow(user.id, limit_per_minute=settings.tile_proxy_rate_limit_per_minute):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Tile rate limit exceeded",
            headers={"Retry-After": "60"},
        )

    key = f"{provider}/{z}/{x}/{y}"
    content = cache.get(key, max_age_seconds=settings.tile_proxy_cache_ttl_seconds)
    cache_state = "hit"
    if content is None:
        if upstream is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Tile provider unavailable",
            )
        try:
            content = upstream.fetch(provider, z, x, y)
        except TileUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Tile provider unavailable",
            ) from None
        cache.put(key, content)
        cache_state = "miss"
    return Response(
        content=content,
        media_type=TILE_MEDIA_TYPE,
        headers={
            "X-Tile-Attribution": settings.tile_proxy_attribution,
            "X-Tile-Cache": cache_state,
            "Cache-Control": f"private, max-age={settings.tile_proxy_cache_ttl_seconds}",
        },
    )
