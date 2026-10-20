"""Explicit database destination for worker commands.

The configured host is never rewritten: guessing a reachable host can write to a
different database that happens to answer on the same local port. A Compose-only
host is accepted when it actually resolves, which is the case inside the Compose
network, and refused with guidance when it does not, which is the case on a
developer machine.
"""

from __future__ import annotations

import socket
from collections.abc import Callable
from urllib.parse import urlsplit

COMPOSE_ONLY_HOSTS = ("postgres",)


def _resolves(host: str) -> bool:
    try:
        socket.getaddrinfo(host, None)
    except OSError:
        return False
    return True


def resolve_database_url(
    requested: str | None,
    configured: str,
    *,
    host_resolves: Callable[[str], bool] = _resolves,
) -> str:
    url = (requested or configured).replace("postgresql+psycopg://", "postgresql://", 1)
    host = urlsplit(url).hostname
    if requested is None and host in COMPOSE_ONLY_HOSTS and not host_resolves(host):
        raise RuntimeError(
            f"configured database host {host!r} is only reachable inside Compose; "
            "pass --database-url with the ZENIT database reachable from here"
        )
    return url
