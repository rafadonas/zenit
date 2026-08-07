from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from zenit_api.config import get_settings


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_settings()
    yield


settings = get_settings()
app = FastAPI(
    title="ZENIT API",
    version=settings.app_version,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Report process health without exposing secrets or dependency details."""

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
