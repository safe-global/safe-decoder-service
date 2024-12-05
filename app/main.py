import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from . import VERSION
from .consumers.queue_consumer import QueueConsumer
from .routers import about, contracts, default


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(QueueConsumer().consume(loop))
        await task
    except Exception as e:
        logging.error("Lifespan error: %s", e)
    yield


app = FastAPI(
    title="Safe Decoder Service",
    description="Safe Core{API} decoder service",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# Router configuration
api_v1_router = APIRouter(
    prefix="/api/v1",
)
api_v1_router.include_router(about.router)
api_v1_router.include_router(contracts.router)
app.include_router(api_v1_router)
app.include_router(default.router)
