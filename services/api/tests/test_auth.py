import asyncio
import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from zenit_api.auth import (
    PASSWORD_HASH,
    AuthenticatedUser,
    RoadRoleAssignment,
    UserIdentity,
    create_access_token,
    decode_access_token,
    get_authentication_session_store,
    get_current_user,
    get_identity_reader,
    get_login_throttle,
    get_road_role_reader,
)
from zenit_api.auth_sessions import AuthenticationSessionRecord
from zenit_api.config import Settings
from zenit_api.login_throttle import LoginThrottlePolicy, digest_login_identifier
from zenit_api.main import app

USER_ID = UUID("10000000-0000-4000-8000-000000000001")
SESSION_ID = UUID("20000000-0000-4000-8000-000000000001")


class FakeIdentityReader:
    def __init__(self, *, password: str = "correct-horse-battery", status: str = "active") -> None:
        self.by_email_calls = 0
        self.identity = UserIdentity(
            id=USER_ID,
            email="manager@example.test",
            display_name="MVP Manager",
            password_hash=PASSWORD_HASH.hash(password),
            status=status,
        )

    async def by_email(self, email: str) -> UserIdentity | None:
        self.by_email_calls += 1
        return self.identity if email.lower() == self.identity.email else None

    async def by_id(self, user_id: UUID) -> UserIdentity | None:
        return self.identity if user_id == self.identity.id else None


class FakeLoginThrottle:
    def __init__(
        self,
        *,
        retry_after: int | None = None,
        failure_retry_after: int | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after
        self.failure_retry_after_seconds = failure_retry_after
        self.checked_digests: list[str] = []
        self.failed_digests: list[str] = []
        self.succeeded_digests: list[str] = []

    async def retry_after(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> int | None:
        del policy, correlation_id, now
        self.checked_digests.append(identifier_digest)
        return self.retry_after_seconds

    async def record_failure(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> int | None:
        del policy, correlation_id, now
        self.failed_digests.append(identifier_digest)
        return self.failure_retry_after_seconds

    async def record_success(
        self,
        identifier_digest: str,
        *,
        policy: LoginThrottlePolicy,
        correlation_id: UUID,
        now: datetime,
    ) -> None:
        del policy, correlation_id, now
        self.succeeded_digests.append(identifier_digest)


class FakeAuthenticationSessionStore:
    def __init__(self) -> None:
        self.sessions: dict[UUID, AuthenticationSessionRecord] = {}
        self.revoked_session_ids: set[UUID] = set()

    async def register(self, session: AuthenticationSessionRecord) -> None:
        self.sessions[session.id] = session

    async def is_active(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        token_issuer: str,
        token_audience: str,
        now: datetime,
    ) -> bool:
        session = self.sessions.get(session_id)
        return bool(
            session
            and session.user_id == user_id
            and session.token_issuer == token_issuer
            and session.token_audience == token_audience
            and session.expires_at > now
            and session_id not in self.revoked_session_ids
        )

    async def revoke(
        self,
        session_id: UUID,
        user_id: UUID,
        *,
        correlation_id: UUID,
        revoked_at: datetime,
    ) -> bool:
        del correlation_id, revoked_at
        session = self.sessions.get(session_id)
        if session is None or session.user_id != user_id:
            return False
        self.revoked_session_ids.add(session_id)
        return True


def test_login_returns_a_scoped_expiring_token_without_password_data() -> None:
    reader = FakeIdentityReader()
    throttle = FakeLoginThrottle()
    session_store = FakeAuthenticationSessionStore()

    async def fake_reader() -> FakeIdentityReader:
        return reader

    async def fake_throttle() -> FakeLoginThrottle:
        return throttle

    async def fake_session_store() -> FakeAuthenticationSessionStore:
        return session_store

    async def request():
        app.dependency_overrides[get_identity_reader] = fake_reader
        app.dependency_overrides[get_login_throttle] = fake_throttle
        app.dependency_overrides[get_authentication_session_store] = fake_session_store
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    "/v1/auth/token",
                    data={"username": "manager@example.test", "password": "correct-horse-battery"},
                )
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 1800
    assert payload["user"]["id"] == str(USER_ID)
    assert "password" not in response.text
    assert decode_access_token(payload["access_token"], Settings()) == USER_ID
    assert throttle.checked_digests == throttle.succeeded_digests
    assert throttle.failed_digests == []
    assert len(session_store.sessions) == 1
    registered_session = next(iter(session_store.sessions.values()))
    assert registered_session.user_id == USER_ID
    assert registered_session.correlation_id == UUID(response.headers["x-correlation-id"])


def test_login_uses_the_same_generic_failure_for_invalid_credentials() -> None:
    reader = FakeIdentityReader()
    throttle = FakeLoginThrottle()
    session_store = FakeAuthenticationSessionStore()

    async def fake_reader() -> FakeIdentityReader:
        return reader

    async def fake_throttle() -> FakeLoginThrottle:
        return throttle

    async def fake_session_store() -> FakeAuthenticationSessionStore:
        return session_store

    async def request():
        app.dependency_overrides[get_identity_reader] = fake_reader
        app.dependency_overrides[get_login_throttle] = fake_throttle
        app.dependency_overrides[get_authentication_session_store] = fake_session_store
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    "/v1/auth/token",
                    data={"username": "manager@example.test", "password": "wrong-password"},
                )
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())

    assert response.status_code == 401
    payload = response.json()
    assert payload["code"] == "authentication_required"
    assert payload["message"] == "Incorrect email or password"
    assert payload["details"] is None
    assert payload["correlation_id"] == response.headers["x-correlation-id"]
    assert response.headers["www-authenticate"] == "Bearer"
    assert throttle.checked_digests == throttle.failed_digests
    assert throttle.succeeded_digests == []


def test_login_throttle_rejects_before_identity_or_password_lookup() -> None:
    reader = FakeIdentityReader()
    throttle = FakeLoginThrottle(retry_after=37)
    session_store = FakeAuthenticationSessionStore()

    async def fake_reader() -> FakeIdentityReader:
        return reader

    async def fake_throttle() -> FakeLoginThrottle:
        return throttle

    async def fake_session_store() -> FakeAuthenticationSessionStore:
        return session_store

    async def request():
        app.dependency_overrides[get_identity_reader] = fake_reader
        app.dependency_overrides[get_login_throttle] = fake_throttle
        app.dependency_overrides[get_authentication_session_store] = fake_session_store
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    "/v1/auth/token",
                    data={"username": "manager@example.test", "password": "wrong-password"},
                )
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())

    assert response.status_code == 429
    assert response.headers["retry-after"] == "37"
    assert response.json()["code"] == "rate_limit_exceeded"
    assert reader.by_email_calls == 0
    assert throttle.failed_digests == []


def test_login_failure_that_reaches_limit_returns_retry_after() -> None:
    reader = FakeIdentityReader()
    throttle = FakeLoginThrottle(failure_retry_after=900)
    session_store = FakeAuthenticationSessionStore()

    async def fake_reader() -> FakeIdentityReader:
        return reader

    async def fake_throttle() -> FakeLoginThrottle:
        return throttle

    async def fake_session_store() -> FakeAuthenticationSessionStore:
        return session_store

    async def request():
        app.dependency_overrides[get_identity_reader] = fake_reader
        app.dependency_overrides[get_login_throttle] = fake_throttle
        app.dependency_overrides[get_authentication_session_store] = fake_session_store
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    "/v1/auth/token",
                    data={"username": "manager@example.test", "password": "wrong-password"},
                )
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())

    assert response.status_code == 429
    assert response.headers["retry-after"] == "900"
    assert throttle.checked_digests == throttle.failed_digests


def test_login_identifier_digest_is_normalized_and_does_not_expose_email() -> None:
    digest = digest_login_identifier(" Manager@Example.Test ", "test-secret")

    assert digest == digest_login_identifier("manager@example.test", "test-secret")
    assert len(digest) == 64
    assert "manager" not in digest


def test_access_token_rejects_an_unexpected_audience() -> None:
    settings = Settings()
    token, _ = create_access_token(
        USER_ID,
        settings,
        now=datetime.now(UTC),
    )
    decoded = jwt.decode(
        token,
        settings.auth_secret_key.get_secret_value(),
        algorithms=["HS256"],
        audience=settings.auth_token_audience,
        issuer=settings.auth_token_issuer,
    )
    decoded["aud"] = "another-api"
    tampered_audience_token = jwt.encode(
        decoded,
        settings.auth_secret_key.get_secret_value(),
        algorithm="HS256",
    )

    try:
        decode_access_token(tampered_audience_token, settings)
    except jwt.InvalidAudienceError:
        pass
    else:
        raise AssertionError("unexpected JWT audience must be rejected")


def test_logout_revokes_a_registered_session_and_is_idempotent() -> None:
    settings = Settings()
    issued_at = datetime.now(UTC)
    token, expires_in = create_access_token(
        USER_ID,
        settings,
        now=issued_at,
        session_id=SESSION_ID,
    )
    reader = FakeIdentityReader()
    session_store = FakeAuthenticationSessionStore()

    async def fake_reader() -> FakeIdentityReader:
        return reader

    async def fake_session_store() -> FakeAuthenticationSessionStore:
        return session_store

    class FakeRoadRoleReader:
        async def for_user(self, user_id: UUID) -> tuple[RoadRoleAssignment, ...]:
            assert user_id == USER_ID
            return ()

    async def fake_roles() -> FakeRoadRoleReader:
        return FakeRoadRoleReader()

    async def request() -> tuple[int, int, int, int]:
        await session_store.register(
            AuthenticationSessionRecord(
                id=SESSION_ID,
                user_id=USER_ID,
                token_issuer=settings.auth_token_issuer,
                token_audience=settings.auth_token_audience,
                issued_at=issued_at,
                expires_at=issued_at + timedelta(seconds=expires_in),
                correlation_id=UUID("30000000-0000-4000-8000-000000000001"),
            )
        )
        app.dependency_overrides[get_identity_reader] = fake_reader
        app.dependency_overrides[get_authentication_session_store] = fake_session_store
        app.dependency_overrides[get_road_role_reader] = fake_roles
        try:
            transport = ASGITransport(app=app)
            headers = {"Authorization": f"Bearer {token}"}
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                before = await client.get("/v1/auth/me", headers=headers)
                first = await client.post("/v1/auth/logout", headers=headers)
                second = await client.post("/v1/auth/logout", headers=headers)
                after = await client.get("/v1/auth/me", headers=headers)
                return before.status_code, first.status_code, second.status_code, after.status_code
        finally:
            app.dependency_overrides.clear()

    before_status, first_status, second_status, after_status = asyncio.run(request())

    assert before_status == 200
    assert first_status == 204
    assert second_status == 204
    assert after_status == 401
    assert session_store.revoked_session_ids == {SESSION_ID}


def test_signed_token_without_a_registered_session_is_rejected() -> None:
    token, _ = create_access_token(USER_ID, Settings(), session_id=SESSION_ID)
    reader = FakeIdentityReader()
    session_store = FakeAuthenticationSessionStore()

    async def fake_reader() -> FakeIdentityReader:
        return reader

    async def fake_session_store() -> FakeAuthenticationSessionStore:
        return session_store

    async def request() -> tuple[int, int]:
        app.dependency_overrides[get_identity_reader] = fake_reader
        app.dependency_overrides[get_authentication_session_store] = fake_session_store
        try:
            transport = ASGITransport(app=app)
            headers = {"Authorization": f"Bearer {token}"}
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                context = await client.get("/v1/auth/me", headers=headers)
                logout = await client.post("/v1/auth/logout", headers=headers)
                return context.status_code, logout.status_code
        finally:
            app.dependency_overrides.clear()

    assert asyncio.run(request()) == (401, 401)


def test_staging_rejects_the_development_signing_secret() -> None:
    with pytest.raises(ValidationError, match="AUTH_SECRET_KEY"):
        Settings(app_env="staging")


def test_login_throttle_policy_version_rejects_untracked_free_text() -> None:
    with pytest.raises(ValidationError, match="auth_login_throttle_policy_version"):
        Settings(auth_login_throttle_policy_version=" untracked policy ")


def test_media_encryption_key_requires_exactly_32_base64_encoded_bytes() -> None:
    with pytest.raises(ValidationError, match="must decode to 32 bytes"):
        Settings(object_storage_media_encryption_key="dG9vLXNob3J0")

    with pytest.raises(ValidationError, match="must be valid base64"):
        Settings(object_storage_media_encryption_key="not base64!")


def test_staging_requires_https_object_storage() -> None:
    with pytest.raises(ValidationError, match="OBJECT_STORAGE_ENDPOINT must use HTTPS"):
        Settings(
            app_env="staging",
            auth_secret_key="a" * 32,
            object_storage_secret_key="non-default-secret",
            object_storage_media_encryption_key=base64.b64encode(b"k" * 32).decode(),
        )


def test_authenticated_context_exposes_only_the_current_users_scoped_roles() -> None:
    user = AuthenticatedUser(
        id=USER_ID,
        email="manager@example.test",
        display_name="MVP Manager",
    )

    class FakeRoleReader:
        async def for_user(self, user_id: UUID) -> tuple[RoadRoleAssignment, ...]:
            assert user_id == USER_ID
            return (
                RoadRoleAssignment(
                    road_code="SP021",
                    role="manager",
                    data_status="prepared",
                ),
            )

    async def fake_user() -> AuthenticatedUser:
        return user

    async def fake_roles() -> FakeRoleReader:
        return FakeRoleReader()

    async def request():
        app.dependency_overrides[get_current_user] = fake_user
        app.dependency_overrides[get_road_role_reader] = fake_roles
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get("/v1/auth/me")
        finally:
            app.dependency_overrides.clear()

    response = asyncio.run(request())

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": str(USER_ID),
            "email": "manager@example.test",
            "display_name": "MVP Manager",
        },
        "road_roles": [
            {"road_code": "SP021", "role": "manager", "data_status": "prepared"}
        ],
    }


def test_authenticated_context_requires_a_bearer_token() -> None:
    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/v1/auth/me")

    response = asyncio.run(request())

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
