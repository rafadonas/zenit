"""Persistent, privacy-preserving throttling for local MVP authentication."""

from __future__ import annotations

import hashlib
import hmac
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Protocol
from uuid import UUID

import psycopg


@dataclass(frozen=True, slots=True)
class LoginThrottlePolicy:
    version: str
    attempt_limit: int
    window: timedelta
    block_duration: timedelta


@dataclass(frozen=True, slots=True)
class LoginThrottleState:
    failed_attempt_count: int
    window_started_at: datetime
    blocked_until: datetime | None
    policy_version: str


def advance_login_failure(
    current: LoginThrottleState | None,
    *,
    policy: LoginThrottlePolicy,
    now: datetime,
) -> LoginThrottleState:
    block_expired = (
        current is not None
        and current.blocked_until is not None
        and now >= current.blocked_until
    )
    if (
        current is None
        or current.policy_version != policy.version
        or now >= current.window_started_at + policy.window
        or block_expired
    ):
        failed_attempt_count = 1
        window_started_at = now
    else:
        failed_attempt_count = current.failed_attempt_count + 1
        window_started_at = current.window_started_at
    blocked_until = (
        now + policy.block_duration
        if failed_attempt_count >= policy.attempt_limit
        else None
    )
    return LoginThrottleState(
        failed_attempt_count=failed_attempt_count,
        window_started_at=window_started_at,
        blocked_until=blocked_until,
        policy_version=policy.version,
    )


class LoginThrottle(Protocol):
    async def retry_after(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> int | None: ...

    async def record_failure(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> int | None: ...

    async def record_success(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> None: ...


def digest_login_identifier(identifier: str, secret: str) -> str:
    normalized = identifier.strip().lower().encode("utf-8")
    return hmac.new(secret.encode("utf-8"), normalized, hashlib.sha256).hexdigest()


class PostgresLoginThrottleRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )

    async def retry_after(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> int | None:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await self._lock(cursor, identifier_digest)
            await cursor.execute(
                """
                SELECT blocked_until, policy_version
                FROM authentication_login_throttle
                WHERE identifier_digest = %s
                """,
                (identifier_digest,),
            )
            row = await cursor.fetchone()
            blocked_until = (
                row[0] if row is not None and row[1] == policy.version else None
            )
            if blocked_until is None or blocked_until <= now:
                return None
            await self._record_attempt(
                cursor,
                identifier_digest,
                "blocked",
                policy.version,
                correlation_id,
                now,
            )
            return self._remaining_seconds(blocked_until, now)

    async def record_failure(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> int | None:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await self._lock(cursor, identifier_digest)
            await cursor.execute(
                """
                SELECT failed_attempt_count, window_started_at, blocked_until, policy_version
                FROM authentication_login_throttle
                WHERE identifier_digest = %s
                FOR UPDATE
                """,
                (identifier_digest,),
            )
            row = await cursor.fetchone()
            if (
                row is not None
                and row[3] == policy.version
                and row[2] is not None
                and row[2] > now
            ):
                await self._record_attempt(
                    cursor,
                    identifier_digest,
                    "blocked",
                    policy.version,
                    correlation_id,
                    now,
                )
                return self._remaining_seconds(row[2], now)

            current = (
                LoginThrottleState(
                    failed_attempt_count=row[0],
                    window_started_at=row[1],
                    blocked_until=row[2],
                    policy_version=row[3],
                )
                if row is not None
                else None
            )
            next_state = advance_login_failure(current, policy=policy, now=now)
            await cursor.execute(
                """
                INSERT INTO authentication_login_throttle (
                    identifier_digest,
                    failed_attempt_count,
                    window_started_at,
                    blocked_until,
                    policy_version,
                    updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (identifier_digest) DO UPDATE SET
                    failed_attempt_count = EXCLUDED.failed_attempt_count,
                    window_started_at = EXCLUDED.window_started_at,
                    blocked_until = EXCLUDED.blocked_until,
                    policy_version = EXCLUDED.policy_version,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    identifier_digest,
                    next_state.failed_attempt_count,
                    next_state.window_started_at,
                    next_state.blocked_until,
                    policy.version,
                    now,
                ),
            )
            await self._record_attempt(
                cursor,
                identifier_digest,
                "failed",
                policy.version,
                correlation_id,
                now,
            )
            if next_state.blocked_until is None:
                return None
            return self._remaining_seconds(next_state.blocked_until, now)

    async def record_success(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> None:
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await self._lock(cursor, identifier_digest)
            await cursor.execute(
                "DELETE FROM authentication_login_throttle WHERE identifier_digest = %s",
                (identifier_digest,),
            )
            await self._record_attempt(
                cursor,
                identifier_digest,
                "succeeded",
                policy.version,
                correlation_id,
                now,
            )

    @staticmethod
    async def _lock(cursor: psycopg.AsyncCursor[tuple], identifier_digest: str) -> None:
        await cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"authentication-login:{identifier_digest}",),
        )

    @staticmethod
    async def _record_attempt(
        cursor: psycopg.AsyncCursor[tuple],
        identifier_digest: str,
        outcome: Literal["succeeded", "failed", "blocked"],
        policy_version: str,
        correlation_id: UUID,
        occurred_at: datetime,
    ) -> None:
        await cursor.execute(
            """
            INSERT INTO authentication_login_attempt (
                identifier_digest,
                outcome,
                policy_version,
                correlation_id,
                occurred_at
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                identifier_digest,
                outcome,
                policy_version,
                correlation_id,
                occurred_at,
            ),
        )

    @staticmethod
    def _remaining_seconds(blocked_until: datetime, now: datetime) -> int:
        return max(1, math.ceil((blocked_until - now).total_seconds()))
