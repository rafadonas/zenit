from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, Protocol
from uuid import UUID, uuid4

import jwt
import psycopg
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pydantic import BaseModel

from zenit_api.auth_sessions import (
    AuthenticationSessionRecord,
    AuthenticationSessionStore,
    PostgresAuthenticationSessionRepository,
)
from zenit_api.config import Settings, get_settings
from zenit_api.error_contract import ApiErrorResponse
from zenit_api.login_throttle import (
    LoginThrottle,
    LoginThrottlePolicy,
    PostgresLoginThrottleRepository,
    digest_login_identifier,
)

TOKEN_ALGORITHM = "HS256"
PASSWORD_HASH = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = PASSWORD_HASH.hash("zenit-dummy-password-for-timing-equality")


@dataclass(frozen=True, slots=True)
class UserIdentity:
    id: UUID
    email: str
    display_name: str
    password_hash: str
    status: str


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: UUID
    email: str
    display_name: str


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: UUID
    session_id: UUID
    token_issuer: str
    token_audience: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: AuthenticatedUser
    session_id: UUID


@dataclass(frozen=True, slots=True)
class RoadRoleAssignment:
    road_code: str
    role: Literal["manager", "supervisor"]
    data_status: Literal["real", "prepared", "simulated"]


class IdentityReader(Protocol):
    async def by_email(self, email: str) -> UserIdentity | None: ...

    async def by_id(self, user_id: UUID) -> UserIdentity | None: ...


class RoadRoleReader(Protocol):
    async def for_user(self, user_id: UUID) -> tuple[RoadRoleAssignment, ...]: ...


class PostgresIdentityRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def by_email(self, email: str) -> UserIdentity | None:
        return await self._one("lower(email) = lower(%s)", email)

    async def by_id(self, user_id: UUID) -> UserIdentity | None:
        return await self._one("id = %s", user_id)

    async def for_user(self, user_id: UUID) -> tuple[RoadRoleAssignment, ...]:
        query = """
            SELECT road.code, assignment.role, assignment.data_status
            FROM road_user_role assignment
            JOIN road ON road.id = assignment.road_id
            WHERE assignment.user_id = %s
            ORDER BY road.code, assignment.role
        """
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(query, (user_id,))
            rows = await cursor.fetchall()
        return tuple(
            RoadRoleAssignment(
                road_code=row[0],
                role=row[1],
                data_status=row[2],
            )
            for row in rows
        )

    async def _one(self, predicate: str, value: object) -> UserIdentity | None:
        query = f"""
            SELECT id, email, display_name, password_hash, status
            FROM app_user
            WHERE {predicate}
        """
        connection = await psycopg.AsyncConnection.connect(self._database_url)
        async with connection, connection.cursor() as cursor:
            await cursor.execute(query, (value,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return UserIdentity(
            id=row[0],
            email=row[1],
            display_name=row[2],
            password_hash=row[3],
            status=row[4],
        )


class AuthenticatedUserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthenticatedUserResponse


class RoadRoleResponse(BaseModel):
    road_code: str
    role: Literal["manager", "supervisor"]
    data_status: Literal["real", "prepared", "simulated"]


class AuthenticatedContextResponse(BaseModel):
    user: AuthenticatedUserResponse
    road_roles: list[RoadRoleResponse]


async def get_identity_reader() -> IdentityReader:
    return PostgresIdentityRepository(get_settings().database_url)


async def get_road_role_reader() -> RoadRoleReader:
    return PostgresIdentityRepository(get_settings().database_url)


async def get_auth_settings() -> Settings:
    return get_settings()


async def get_login_throttle() -> LoginThrottle:
    return PostgresLoginThrottleRepository(get_settings().database_url)


async def get_authentication_session_store() -> AuthenticationSessionStore:
    return PostgresAuthenticationSessionRepository(get_settings().database_url)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")


def create_access_token(
    user_id: UUID,
    settings: Settings,
    *,
    now: datetime | None = None,
    session_id: UUID | None = None,
) -> tuple[str, int]:
    issued_at = now or datetime.now(UTC)
    expires_in = settings.auth_access_token_minutes * 60
    payload = {
        "sub": str(user_id),
        "iss": settings.auth_token_issuer,
        "aud": settings.auth_token_audience,
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=expires_in),
        "jti": str(session_id or uuid4()),
    }
    token = jwt.encode(
        payload,
        settings.auth_secret_key.get_secret_value(),
        algorithm=TOKEN_ALGORITHM,
    )
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> UUID:
    return decode_access_token_claims(token, settings).user_id


def decode_access_token_claims(token: str, settings: Settings) -> AccessTokenClaims:
    payload = jwt.decode(
        token,
        settings.auth_secret_key.get_secret_value(),
        algorithms=[TOKEN_ALGORITHM],
        audience=settings.auth_token_audience,
        issuer=settings.auth_token_issuer,
        options={"require": ["sub", "iss", "aud", "iat", "exp", "jti"]},
    )
    return AccessTokenClaims(
        user_id=UUID(payload["sub"]),
        session_id=UUID(payload["jti"]),
        token_issuer=payload["iss"],
        token_audience=payload["aud"],
        issued_at=datetime.fromtimestamp(payload["iat"], UTC),
        expires_at=datetime.fromtimestamp(payload["exp"], UTC),
    )


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _login_throttle_policy(settings: Settings) -> LoginThrottlePolicy:
    return LoginThrottlePolicy(
        version=settings.auth_login_throttle_policy_version,
        attempt_limit=settings.auth_login_attempt_limit,
        window=timedelta(seconds=settings.auth_login_window_seconds),
        block_duration=timedelta(seconds=settings.auth_login_block_seconds),
    )


def _login_rate_limit_error(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many login attempts; retry later",
        headers={"Retry-After": str(retry_after)},
    )


async def get_current_session(
    token: Annotated[str, Depends(oauth2_scheme)],
    reader: Annotated[IdentityReader, Depends(get_identity_reader)],
    session_store: Annotated[
        AuthenticationSessionStore, Depends(get_authentication_session_store)
    ],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> AuthenticatedSession:
    try:
        claims = decode_access_token_claims(token, settings)
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise _credentials_error() from None

    if not await session_store.is_active(
        claims.session_id,
        claims.user_id,
        token_issuer=claims.token_issuer,
        token_audience=claims.token_audience,
        now=datetime.now(UTC),
    ):
        raise _credentials_error()

    identity = await reader.by_id(claims.user_id)
    if identity is None or identity.status != "active":
        raise _credentials_error()
    return AuthenticatedSession(
        user=AuthenticatedUser(
            id=identity.id,
            email=identity.email,
            display_name=identity.display_name,
        ),
        session_id=claims.session_id,
    )


async def get_current_user(
    session: Annotated[AuthenticatedSession, Depends(get_current_session)],
) -> AuthenticatedUser:
    return session.user


router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post(
    "/token",
    response_model=AccessTokenResponse,
    responses={
        429: {
            "description": "The normalized login identifier is temporarily throttled.",
            "headers": {
                "Retry-After": {
                    "description": "Seconds until another login attempt is allowed.",
                    "schema": {"type": "integer", "minimum": 1},
                },
                "X-Correlation-ID": {
                    "description": "Request correlation identifier.",
                    "schema": {"type": "string", "format": "uuid"},
                },
            },
            "model": ApiErrorResponse,
        }
    },
)
async def login_for_access_token(
    request: Request,
    username: Annotated[str, Form(min_length=3, max_length=320)],
    password: Annotated[str, Form(min_length=1, max_length=1024)],
    reader: Annotated[IdentityReader, Depends(get_identity_reader)],
    throttle: Annotated[LoginThrottle, Depends(get_login_throttle)],
    session_store: Annotated[
        AuthenticationSessionStore, Depends(get_authentication_session_store)
    ],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> AccessTokenResponse:
    normalized_username = username.strip().lower()
    identifier_digest = digest_login_identifier(
        normalized_username,
        settings.auth_secret_key.get_secret_value(),
    )
    policy = _login_throttle_policy(settings)
    now = datetime.now(UTC)
    request_correlation_id = getattr(request.state, "correlation_id", None)
    correlation_id = (
        request_correlation_id if isinstance(request_correlation_id, UUID) else uuid4()
    )
    retry_after = await throttle.retry_after(
        identifier_digest,
        policy=policy,
        correlation_id=correlation_id,
        now=now,
    )
    if retry_after is not None:
        raise _login_rate_limit_error(retry_after)

    identity = await reader.by_email(normalized_username)
    password_hash = identity.password_hash if identity is not None else _DUMMY_PASSWORD_HASH
    try:
        password_matches = PASSWORD_HASH.verify(password, password_hash)
    except UnknownHashError:
        password_matches = False

    if identity is None or identity.status != "active" or not password_matches:
        retry_after = await throttle.record_failure(
            identifier_digest,
            policy=policy,
            correlation_id=correlation_id,
            now=now,
        )
        if retry_after is not None:
            raise _login_rate_limit_error(retry_after)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await throttle.record_success(
        identifier_digest,
        policy=policy,
        correlation_id=correlation_id,
        now=now,
    )
    issued_at = datetime.now(UTC)
    session_id = uuid4()
    token, expires_in = create_access_token(
        identity.id,
        settings,
        now=issued_at,
        session_id=session_id,
    )
    await session_store.register(
        AuthenticationSessionRecord(
            id=session_id,
            user_id=identity.id,
            token_issuer=settings.auth_token_issuer,
            token_audience=settings.auth_token_audience,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=expires_in),
            correlation_id=correlation_id,
        )
    )
    return AccessTokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=AuthenticatedUserResponse(
            id=identity.id,
            email=identity.email,
            display_name=identity.display_name,
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_session(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    session_store: Annotated[
        AuthenticationSessionStore, Depends(get_authentication_session_store)
    ],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> Response:
    try:
        claims = decode_access_token_claims(token, settings)
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise _credentials_error() from None

    request_correlation_id = getattr(request.state, "correlation_id", None)
    correlation_id = (
        request_correlation_id if isinstance(request_correlation_id, UUID) else uuid4()
    )
    if not await session_store.revoke(
        claims.session_id,
        claims.user_id,
        correlation_id=correlation_id,
        revoked_at=datetime.now(UTC),
    ):
        raise _credentials_error()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AuthenticatedContextResponse)
async def read_authenticated_context(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    role_reader: Annotated[RoadRoleReader, Depends(get_road_role_reader)],
) -> AuthenticatedContextResponse:
    roles = await role_reader.for_user(user.id)
    return AuthenticatedContextResponse(
        user=AuthenticatedUserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
        ),
        road_roles=[
            RoadRoleResponse(
                road_code=role.road_code,
                role=role.role,
                data_status=role.data_status,
            )
            for role in roles
        ],
    )
