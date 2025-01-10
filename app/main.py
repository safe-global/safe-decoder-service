import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from . import VERSION
from .datasources.queue.exceptions import QueueProviderUnableToConnectException
from .datasources.queue.queue_provider import QueueProvider
from .routers import about, admin, contracts, data_decoder, default
from .services.abis import AbiService
from .services.events import EventsService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Define the lifespan of the application:
    - Connects to the QueueProvider at startup.
    - Disconnects from the QueueProvider at shutdown.
    """
    queue_provider = QueueProvider()
    consume_task = None
    abi_service = AbiService()
    try:
        loop = asyncio.get_running_loop()
        try:
            await queue_provider.connect(loop)
        except QueueProviderUnableToConnectException as e:
            logging.error(f"Unable to connect to Queue Provider: {e}")
        if queue_provider.is_connected():
            events_service = EventsService()
            consume_task = asyncio.create_task(
                queue_provider.consume(events_service.process_event)
            )
        await abi_service.load_local_abis_in_database()
        yield
    finally:
        if consume_task:
            consume_task.cancel()
        await queue_provider.disconnect()


app = FastAPI(
    title="Safe Decoder Service",
    description="Safe Core{API} decoder service",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

admin.load_admin(app)

# Router configuration
api_v1_router = APIRouter(
    prefix="/api/v1",
)
api_v1_router.include_router(about.router)
api_v1_router.include_router(contracts.router)
api_v1_router.include_router(data_decoder.router)
app.include_router(api_v1_router)
app.include_router(default.router)
