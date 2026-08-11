import asyncio
import hashlib
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.main import app
from zenit_api.media import (
    PhotoContentMismatchError,
    PhotoManifestNotFoundError,
    PreparedPhotoContent,
    PreparedPhotoUploadResponse,
    get_media_reader,
    get_media_writer,
)

USER_ID = UUID("40000000-0000-4000-8000-000000000001")
DEVICE_ID = UUID("40000000-0000-4000-8000-000000000002")
PHOTO_ID = UUID("40000000-0000-4000-8000-000000000007")
JPEG = b"\xff\xd8\xff\xd9"
ACTOR = AuthenticatedUser(
    id=USER_ID,
    email="field@example.test",
    display_name="Prepared Field User",
)


class FakeMediaWriter:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure

    async def upload(self, **values) -> PreparedPhotoUploadResponse:
        if self.failure is not None:
            raise self.failure
        assert values["actor"] == ACTOR
        assert values["device_id"] == DEVICE_ID
        assert values["photo_id"] == PHOTO_ID
        assert values["content"] == JPEG
        assert values["checksum_sha256"] == hashlib.sha256(JPEG).hexdigest()
        return PreparedPhotoUploadResponse(
            photo_id=PHOTO_ID,
            checksum_sha256=values["checksum_sha256"],
            byte_size=len(JPEG),
            media_type="image/jpeg",
        )


class FakeMediaReader:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure

    async def retrieve(self, **values) -> PreparedPhotoContent:
        if self.failure is not None:
            raise self.failure
        assert values == {"actor": ACTOR, "photo_id": PHOTO_ID}
        return PreparedPhotoContent(
            content=JPEG,
            media_type="image/jpeg",
            checksum_sha256=hashlib.sha256(JPEG).hexdigest(),
        )


def request_upload(
    *,
    content: bytes = JPEG,
    media_type: str = "image/jpeg",
    failure: Exception | None = None,
    authenticated: bool = True,
):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_writer() -> FakeMediaWriter:
        return FakeMediaWriter(failure)

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_media_writer] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/media/{PHOTO_ID}",
                    headers={"X-Zenit-Device-ID": str(DEVICE_ID)},
                    files={"file": ("point.jpg", content, media_type)},
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_upload_verifies_content_and_returns_only_unverified_prepared_status() -> None:
    response = request_upload()

    assert response.status_code == 200
    payload = response.json()
    assert payload["checksum_sha256"] == hashlib.sha256(JPEG).hexdigest()
    assert payload["content_status"] == "uploaded_unverified"
    assert payload["ruler_status"] == "not_validated"
    assert payload["quality_status"] == "prepared_unverified"
    assert payload["eligible_for_official_reporting"] is False
    assert payload["persisted"] is True


def test_upload_rejects_media_type_and_signature_mismatch() -> None:
    assert request_upload(media_type="text/plain").status_code == 415
    assert request_upload(content=b"not-a-jpeg").status_code == 422
    assert request_upload(content=b"").status_code == 413


def test_upload_hides_missing_or_unauthorized_manifest_and_reports_conflict() -> None:
    missing = request_upload(failure=PhotoManifestNotFoundError())
    conflict = request_upload(failure=PhotoContentMismatchError())

    assert missing.status_code == 404
    assert conflict.status_code == 409


def test_upload_requires_authentication() -> None:
    response = request_upload(authenticated=False)

    assert response.status_code == 401


def request_retrieval(*, failure: Exception | None = None, authenticated: bool = True):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_reader() -> FakeMediaReader:
        return FakeMediaReader(failure)

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_media_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(f"/v1/media/{PHOTO_ID}")
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_retrieval_returns_verified_prepared_content_without_cache() -> None:
    response = request_retrieval()

    assert response.status_code == 200
    assert response.content == JPEG
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-zenit-checksum-sha256"] == hashlib.sha256(JPEG).hexdigest()
    assert response.headers["x-zenit-ruler-status"] == "not_validated"
    assert response.headers["x-zenit-quality-status"] == "prepared_unverified"
    assert response.headers["x-zenit-eligible-for-official-reporting"] == "false"


def test_retrieval_hides_unauthorized_photo_and_reports_integrity_failure() -> None:
    missing = request_retrieval(failure=PhotoManifestNotFoundError())
    corrupt = request_retrieval(failure=PhotoContentMismatchError())

    assert missing.status_code == 404
    assert corrupt.status_code == 409


def test_retrieval_requires_authentication() -> None:
    assert request_retrieval(authenticated=False).status_code == 401
