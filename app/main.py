import asyncio

from fastapi import APIRouter, FastAPI

from . import VERSION
from .consumers.queue_consumer import QueueConsumer
from .routers import about, default

app = FastAPI(
    title="Safe Decoder Service",
    description="Safe Core{API} decoder service",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
)

# Router configuration
api_v1_router = APIRouter(
    prefix="/api/v1",
)
api_v1_router.include_router(about.router)
app.include_router(api_v1_router)
app.include_router(default.router)


@app.on_event("startup")
async def startup():
    loop = asyncio.get_running_loop()
    task = loop.create_task(QueueConsumer().consume(loop))
    await task
