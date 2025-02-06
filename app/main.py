import asyncio
import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from starlette.requests import Request

from . import VERSION
from .custom_logger import HttpRequestLog, HttpResponseLog
from .datasources.db.database import (
    _get_database_session_context,
    db_session,
    set_database_session_context,
)
from .datasources.queue.exceptions import QueueProviderUnableToConnectException
from .datasources.queue.queue_provider import QueueProvider
from .routers import about, admin, contracts, data_decoder, default
from .services.abis import AbiService
from .services.events import EventsService

logger = logging.getLogger()


def log_record_factory_for_request(*args, **kwargs) -> logging.LogRecord:
    """
    Inject session database identifier in log record.

    :param args:
    :param kwargs:
    :return:
    """
    # Create a log record with additional context
    record = logging.LogRecord(*args, **kwargs)
    try:
        record.db_session = _get_database_session_context()
    except LookupError:
        # This error means that there is not session
        pass

    return record


logging.setLogRecordFactory(log_record_factory_for_request)


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
            logger.error(f"Unable to connect to Queue Provider {e}")
        if queue_provider.is_connected():
            events_service = EventsService()
            consume_task = asyncio.create_task(
                queue_provider.consume(events_service.process_event)
            )
        with set_database_session_context("LoadAbisOnStartup"):
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


@app.middleware("http")
async def http_request_middleware(request: Request, call_next):
    """
    Intercepts request and do some actions:
     - Set the database session context for the current request, so the same database session is used across the whole request.
     - Log requests calls

    :param request:
    :param call_next:
    :return:
    """
    start_time = datetime.datetime.now(datetime.timezone.utc)
    with set_database_session_context():
        try:
            response = await call_next(request)
        except Exception as e:
            raise e
        finally:
            await db_session.remove()
            # Log request
            try:
                end_time = datetime.datetime.now(datetime.timezone.utc)
                total_time = (
                    end_time - start_time
                ).total_seconds() * 1000  # time in ms
                http_request = HttpRequestLog(
                    url=str(request.url),
                    method=request.method,
                    startTime=start_time,
                )
                http_response = HttpResponseLog(
                    status=response.status_code,
                    endTime=end_time,
                    totalTime=int(total_time),
                )
                logger.info(
                    "Http request",
                    extra={
                        "http_response": http_response.model_dump(),
                        "http_request": http_request.model_dump(),
                    },
                )
            except ValueError as e:
                logger.error(f"Validation log error {e}")

    return response
