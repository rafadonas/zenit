import asyncio
import hashlib
from uuid import UUID

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient

from zenit_api.auth import AuthenticatedUser, get_current_user
from zenit_api.config import Settings
from zenit_api.main import app
from zenit_api.media import (
    PhotoContentMismatchError,
    PhotoManifestNotFoundError,
    StoredObject,
)
from zenit_api.mowing_media import (
    MowingPostServiceMediaService,
    MowingPostServicePhotoContent,
    MowingPostServicePhotoUploadResponse,
    get_mowing_media_reader,
    get_mowing_media_writer,
)

USER_ID = UUID("40000000-0000-4000-8000-000000000001")
DEVICE_ID = UUID("40000000-0000-4000-8000-000000000002")
PHOTO_ID = UUID("40000000-0000-4000-8000-000000000008")
JPEG = b"\xff\xd8\xff\xd9"
ACTOR = AuthenticatedUser(
    id=USER_ID,
    email="field@example.test",
    display_name="Prepared Field User",
)


class FakeMowingMediaWriter:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure

    async def upload(self, **values) -> MowingPostServicePhotoUploadResponse:
        if self.failure is not None:
            raise self.failure
        assert values["actor"] == ACTOR
        assert values["device_id"] == DEVICE_ID
        assert values["photo_id"] == PHOTO_ID
        assert values["content"] == JPEG
        assert values["checksum_sha256"] == hashlib.sha256(JPEG).hexdigest()
        return MowingPostServicePhotoUploadResponse(
            photo_id=PHOTO_ID,
            checksum_sha256=values["checksum_sha256"],
            byte_size=len(JPEG),
            media_type="image/jpeg",
        )


class FakeMowingMediaReader:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure

    async def retrieve(self, **values) -> MowingPostServicePhotoContent:
        if self.failure is not None:
            raise self.failure
        assert values == {"actor": ACTOR, "photo_id": PHOTO_ID}
        return MowingPostServicePhotoContent(
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

    async def fake_writer() -> FakeMowingMediaWriter:
        return FakeMowingMediaWriter(failure)

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_mowing_media_writer] = fake_writer
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post(
                    f"/v1/mowing-media/{PHOTO_ID}",
                    headers={"X-Zenit-Device-ID": str(DEVICE_ID)},
                    files={"file": ("post-service.jpg", content, media_type)},
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_upload_returns_only_simulated_unverified_non_operational_status() -> None:
    response = request_upload()

    assert response.status_code == 200
    payload = response.json()
    assert payload["checksum_sha256"] == hashlib.sha256(JPEG).hexdigest()
    assert payload["phase"] == "post_service"
    assert payload["photo_scope"] == "mowing_demo_post_service_only"
    assert payload["content_status"] == "uploaded_unverified"
    assert payload["ruler_status"] == "not_validated"
    assert payload["location_status"] == "not_collected"
    assert payload["quality_status"] == "simulated_unverified"
    assert payload["data_status"] == "simulated"
    assert payload["operational_approval_satisfied"] is False
    assert payload["authorizes_field_work"] is False
    assert payload["eligible_for_field_execution"] is False
    assert payload["eligible_for_model_training"] is False
    assert payload["eligible_for_official_reporting"] is False
    assert payload["persisted"] is True


def test_upload_rejects_type_signature_and_size_boundaries() -> None:
    assert request_upload(media_type="text/plain").status_code == 415
    assert request_upload(content=b"not-a-jpeg").status_code == 422
    assert request_upload(content=b"").status_code == 413


def test_upload_hides_manifest_and_reports_content_conflict() -> None:
    missing = request_upload(failure=PhotoManifestNotFoundError())
    conflict = request_upload(failure=PhotoContentMismatchError())

    assert missing.status_code == 404
    assert conflict.status_code == 409


def test_upload_requires_authentication() -> None:
    assert request_upload(authenticated=False).status_code == 401


def request_retrieval(*, failure: Exception | None = None, authenticated: bool = True):
    async def fake_actor() -> AuthenticatedUser:
        return ACTOR

    async def fake_reader() -> FakeMowingMediaReader:
        return FakeMowingMediaReader(failure)

    async def request():
        if authenticated:
            app.dependency_overrides[get_current_user] = fake_actor
        app.dependency_overrides[get_mowing_media_reader] = fake_reader
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.get(f"/v1/mowing-media/{PHOTO_ID}")
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(request())


def test_retrieval_returns_only_simulated_unverified_content_without_cache() -> None:
    response = request_retrieval()

    assert response.status_code == 200
    assert response.content == JPEG
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-zenit-phase"] == "post_service"
    assert response.headers["x-zenit-photo-scope"] == "mowing_demo_post_service_only"
    assert response.headers["x-zenit-content-status"] == "uploaded_unverified"
    assert response.headers["x-zenit-ruler-status"] == "not_validated"
    assert response.headers["x-zenit-location-status"] == "not_collected"
    assert response.headers["x-zenit-quality-status"] == "simulated_unverified"
    assert response.headers["x-zenit-data-status"] == "simulated"
    assert response.headers["x-zenit-operational-approval-satisfied"] == "false"
    assert response.headers["x-zenit-authorizes-field-work"] == "false"
    assert response.headers["x-zenit-eligible-for-field-execution"] == "false"
    assert response.headers["x-zenit-eligible-for-model-training"] == "false"
    assert response.headers["x-zenit-eligible-for-official-reporting"] == "false"


def test_retrieval_hides_unauthorized_photo_and_reports_integrity_failure() -> None:
    missing = request_retrieval(failure=PhotoManifestNotFoundError())
    corrupt = request_retrieval(failure=PhotoContentMismatchError())

    assert missing.status_code == 404
    assert corrupt.status_code == 409


def test_retrieval_requires_authentication() -> None:
    assert request_retrieval(authenticated=False).status_code == 401


class FakeCursor:
    def __init__(self, receipt: tuple | None = None) -> None:
        self.receipt = receipt
        self.query = ""
        self.executions: list[tuple[str, tuple]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def execute(self, query: str, parameters: tuple) -> None:
        self.query = query
        self.executions.append((query, parameters))

    async def fetchone(self) -> tuple | None:
        if "FROM prepared_mowing_post_service_photo_manifest" in self.query:
            return (
                UUID("40000000-0000-4000-8000-000000000009"),
                hashlib.sha256(JPEG).hexdigest(),
                len(JPEG),
                "image/jpeg",
            )
        if "FROM prepared_mowing_post_service_photo_upload_receipt" in self.query:
            return self.receipt
        raise AssertionError("unexpected fetchone query")


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self._cursor


class FakeStore:
    def __init__(self, existing: bytes | None = None) -> None:
        self.existing = existing
        self.put_values: dict | None = None
        self.get_values: dict | None = None

    def put_verified(self, **values) -> StoredObject:
        self.put_values = values
        return StoredObject(
            bucket="zenit-media",
            name=(
                "simulated-mowing-post-service-photos/"
                f"{PHOTO_ID}/{hashlib.sha256(JPEG).hexdigest()}.aesgcm"
            ),
            version_id="version-1",
            etag="etag-1",
        )

    def get_verified(self, **values) -> bytes:
        self.get_values = values
        return self.existing if self.existing is not None else JPEG


def test_service_encrypts_into_separate_namespace_and_inserts_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = FakeCursor()
    store = FakeStore()

    async def connect(database_url: str) -> FakeConnection:
        assert database_url.startswith("postgresql://")
        return FakeConnection(cursor)

    async def run_inline(function, **values):
        return function(**values)

    monkeypatch.setattr(psycopg.AsyncConnection, "connect", connect)
    monkeypatch.setattr(asyncio, "to_thread", run_inline)
    service = MowingPostServiceMediaService(Settings(), store=store)  # type: ignore[arg-type]
    response = asyncio.run(
        service.upload(
            actor=ACTOR,
            device_id=DEVICE_ID,
            photo_id=PHOTO_ID,
            content=JPEG,
            media_type="image/jpeg",
            checksum_sha256=hashlib.sha256(JPEG).hexdigest(),
        )
    )

    assert response.data_status == "simulated"
    assert store.put_values is not None
    assert store.put_values["object_prefix"] == "simulated-mowing-post-service-photos"
    assert store.put_values["data_status"] == "simulated"
    assert any(
        "INSERT INTO prepared_mowing_post_service_photo_upload_receipt" in query
        for query, _ in cursor.executions
    )


def test_service_idempotency_decrypts_and_matches_existing_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checksum = hashlib.sha256(JPEG).hexdigest()
    cursor = FakeCursor(
        receipt=(
            f"simulated-mowing-post-service-photos/{PHOTO_ID}/{checksum}.aesgcm",
            "version-1",
            checksum,
            len(JPEG),
            "image/jpeg",
        )
    )
    store = FakeStore(existing=JPEG)

    async def connect(database_url: str) -> FakeConnection:
        return FakeConnection(cursor)

    async def run_inline(function, **values):
        return function(**values)

    monkeypatch.setattr(psycopg.AsyncConnection, "connect", connect)
    monkeypatch.setattr(asyncio, "to_thread", run_inline)
    service = MowingPostServiceMediaService(Settings(), store=store)  # type: ignore[arg-type]
    response = asyncio.run(
        service.upload(
            actor=ACTOR,
            device_id=DEVICE_ID,
            photo_id=PHOTO_ID,
            content=JPEG,
            media_type="image/jpeg",
            checksum_sha256=checksum,
        )
    )

    assert response.persisted is True
    assert store.put_values is None
    assert store.get_values == {
        "name": f"simulated-mowing-post-service-photos/{PHOTO_ID}/{checksum}.aesgcm",
        "version_id": "version-1",
    }

    store.existing = b"different-content"
    with pytest.raises(PhotoContentMismatchError):
        asyncio.run(
            service.upload(
                actor=ACTOR,
                device_id=DEVICE_ID,
                photo_id=PHOTO_ID,
                content=JPEG,
                media_type="image/jpeg",
                checksum_sha256=checksum,
            )
        )


def test_service_retrieval_verifies_exact_version_and_records_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checksum = hashlib.sha256(JPEG).hexdigest()
    cursor = FakeCursor(
        receipt=(
            f"simulated-mowing-post-service-photos/{PHOTO_ID}/{checksum}.aesgcm",
            "version-1",
            checksum,
            len(JPEG),
            "image/jpeg",
        )
    )
    store = FakeStore(existing=JPEG)

    async def connect(database_url: str) -> FakeConnection:
        return FakeConnection(cursor)

    async def run_inline(function, **values):
        return function(**values)

    monkeypatch.setattr(psycopg.AsyncConnection, "connect", connect)
    monkeypatch.setattr(asyncio, "to_thread", run_inline)
    service = MowingPostServiceMediaService(Settings(), store=store)  # type: ignore[arg-type]
    result = asyncio.run(service.retrieve(actor=ACTOR, photo_id=PHOTO_ID))

    assert result.content == JPEG
    assert result.checksum_sha256 == checksum
    assert store.get_values == {
        "name": f"simulated-mowing-post-service-photos/{PHOTO_ID}/{checksum}.aesgcm",
        "version_id": "version-1",
    }
    assert any(
        "INSERT INTO prepared_mowing_post_service_photo_access_event" in query
        for query, _ in cursor.executions
    )

    store.existing = b"different-content"
    with pytest.raises(PhotoContentMismatchError):
        asyncio.run(service.retrieve(actor=ACTOR, photo_id=PHOTO_ID))
