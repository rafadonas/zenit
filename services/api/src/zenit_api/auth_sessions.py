"""Persistent access-token session registration and revocation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

import psycopg


@dataclass(frozen=True, slots=True)
class AuthenticationSessionRecord:
    id: UUID
    user_id: UUID
    token_issuer: str
    token_audience: str
    issued_at: datetime
    expires_at: datetime
    correlation_id: UUID


class AuthenticationSessionStore(Protocol):
    async def register(self, session: AuthenticationSessionRecord) -> None: ...

    async def is_active(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        token_issuer: str,
        token_audience: str,
        now: datetime,
    ) -> bool: ...

    async def revoke(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        correlation_id: UUID,
        revoked_at: datetime,
    ) -> bool: ...


class PostgresAuthenticationSessionRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )

    async def register(self, session: AuthenticationSessionRecord) -> None:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO authentication_session (
                    id,
                    user_id,
                    token_issuer,
                    token_audience,
                    issued_at,
                    expires_at,
                    correlation_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session.id,
                    session.user_id,
                    session.token_issuer,
                    session.token_audience,
                    session.issued_at,
                    session.expires_at,
                    session.correlation_id,
                ),
            )

    async def is_active(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        token_issuer: str,
        token_audience: str,
        now: datetime,
    ) -> bool:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM authentication_session session
                    WHERE session.id = %s
                      AND session.user_id = %s
                      AND session.token_issuer = %s
                      AND session.token_audience = %s
                      AND session.expires_at > %s
                      AND NOT EXISTS (
                          SELECT 1
                          FROM authentication_session_revocation revocation
                          WHERE revocation.session_id = session.id
                      )
                )
                """,
                (
                    session_id,
                    user_id,
                    token_issuer,
                    token_audience,
                    now,
                ),
            )
            row = await cursor.fetchone()
        return bool(row and row[0])

    async def revoke(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        correlation_id: UUID,
        revoked_at: datetime,
    ) -> bool:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(
                """
                WITH owned_session AS (
                    SELECT id
                    FROM authentication_session
                    WHERE id = %s AND user_id = %s
                ), inserted AS (
                    INSERT INTO authentication_session_revocation (
                        session_id,
                        revoked_by_user_id,
                        reason,
                        correlation_id,
                        revoked_at
                    )
                    SELECT id, %s, 'user_logout', %s, %s
                    FROM owned_session
                    ON CONFLICT (session_id) DO NOTHING
                    RETURNING session_id
                )
                SELECT EXISTS (SELECT 1 FROM owned_session)
                """,
                (
                    session_id,
                    user_id,
                    user_id,
                    correlation_id,
                    revoked_at,
                ),
            )
            row = await cursor.fetchone()
        return bool(row and row[0])
