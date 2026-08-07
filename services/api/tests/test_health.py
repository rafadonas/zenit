import asyncio

from httpx import ASGITransport, AsyncClient

from zenit_api.main import app


def test_health_returns_service_metadata() -> None:
    async def request_health():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "zenit",
        "version": "0.1.0",
        "environment": "development",
    }
