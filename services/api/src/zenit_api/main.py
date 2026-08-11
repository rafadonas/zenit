from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from zenit_api.analysis import router as analysis_router
from zenit_api.auth import router as auth_router
from zenit_api.config import get_settings
from zenit_api.inspection_summaries import collection_router as inspection_summary_collection_router
from zenit_api.inspection_summaries import router as inspection_summaries_router
from zenit_api.media import router as media_router
from zenit_api.mobile_sync import router as mobile_sync_router
from zenit_api.mowing_orders import router as mowing_orders_router
from zenit_api.photo_reviews import queue_router as photo_review_queue_router
from zenit_api.photo_reviews import router as photo_reviews_router
from zenit_api.post_inspection_proposals import collection_router as proposal_collection_router
from zenit_api.post_inspection_proposals import summary_router as proposal_summary_router
from zenit_api.recommendation_reviews import router as recommendation_reviews_router
from zenit_api.recommendations import router as recommendations_router
from zenit_api.satellite_observations import router as satellite_observations_router
from zenit_api.segments import router as segments_router
from zenit_api.work_orders import router as work_orders_router


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
app.include_router(analysis_router)
app.include_router(auth_router)
app.include_router(segments_router)
app.include_router(satellite_observations_router)
app.include_router(recommendations_router)
app.include_router(recommendation_reviews_router)
app.include_router(work_orders_router)
app.include_router(mobile_sync_router)
app.include_router(media_router)
app.include_router(mowing_orders_router)
app.include_router(photo_reviews_router)
app.include_router(photo_review_queue_router)
app.include_router(inspection_summaries_router)
app.include_router(inspection_summary_collection_router)
app.include_router(proposal_summary_router)
app.include_router(proposal_collection_router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Report process health without exposing secrets or dependency details."""

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
