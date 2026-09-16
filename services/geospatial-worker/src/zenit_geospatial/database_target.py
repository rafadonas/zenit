"""Explicit database destination for worker commands.

The configured host is never rewritten: guessing a reachable host can write to a
different database that happens to answer on the same local port.
"""

from __future__ import annotations

from urllib.parse import urlsplit

COMPOSE_ONLY_HOSTS = ("postgres",)


def resolve_database_url(requested: str | None, configured: str) -> str:
    url = (requested or configured).replace("postgresql+psycopg://", "postgresql://", 1)
    host = urlsplit(url).hostname
    if requested is None and host in COMPOSE_ONLY_HOSTS:
        raise RuntimeError(
            f"configured database host {host!r} is only reachable inside Compose; "
            "pass --database-url with the ZENIT database reachable from here"
        )
    return url
