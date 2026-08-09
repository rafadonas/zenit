import asyncio
import base64
from datetime import UTC, datetime
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
    get_current_user,
    get_identity_reader,
    get_road_role_reader,
)
from zenit_api.config import Settings
from zenit_api.main import app

USER_ID = UUID("10000000-0000-4000-8000-000000000001")


class FakeIdentityReader:
    def __init__(self, *, password: str = "correct-horse-battery", status: str = "active") -> None:
        self.identity = UserIdentity(
            id=USER_ID,
            email="manager@example.test",
            display_name="MVP Manager",
            password_hash=PASSWORD_HASH.hash(password),
            status=status,
        )

    async def by_email(self, email: str) -> UserIdentity | None:
        return self.identity if email.lower() == self.identity.email else None

    async def by_id(self, user_id: UUID) -> UserIdentity | None:
        return self.identity if user_id == self.identity.id else None


def test_login_returns_a_scoped_expiring_token_without_password_data() -> None:
    reader = FakeIdentityReader()

    async def fake_reader() -> FakeIdentityReader:
        return reader

    async def request():
        app.dependency_overrides[get_identity_reader] = fake_reader
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


def test_login_uses_the_same_generic_failure_for_invalid_credentials() -> None:
    reader = FakeIdentityReader()

    async def fake_reader() -> FakeIdentityReader:
        return reader

    async def request():
        app.dependency_overrides[get_identity_reader] = fake_reader
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
    assert response.json() == {"detail": "Incorrect email or password"}
    assert response.headers["www-authenticate"] == "Bearer"


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


def test_staging_rejects_the_development_signing_secret() -> None:
    with pytest.raises(ValidationError, match="AUTH_SECRET_KEY"):
        Settings(app_env="staging")


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
